"""Tests for how the look for a newer release is run (FC-011 slice 3): one shared time budget, a
branch read without git, the answer the welcome asks for, and the background process.

They sit apart from tests/test_update_check.py, which would otherwise pass the size ceiling.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

from afc import update
from afc.config import set_maintain
from tests.helpers import RemoteCase, git

DAY = 86400


class UpdateBudgetTest(RemoteCase):
    """The look at origin shares one budget however many git calls it takes (FC-011 slice 3: it can
    never run past the time it was given)."""

    TAGS = "".join(f"{'a' * 40}\trefs/tags/{name}\n" for name in ("v0.04a", "v0.03a", "v0.02a"))

    def fake_git(self, delays, calls):
        """subprocess.run standing in for git: each call takes its delay (or its timeout, if that
        is shorter, and then times out); none of the tags is part of main."""
        started = time.monotonic()

        def run(cmd, **kwargs):
            sub = cmd[1]
            delay, timeout = delays.get(sub, 0.5), kwargs["timeout"]
            calls.append((sub, time.monotonic() - started, timeout))
            time.sleep(min(delay, timeout))
            if delay > timeout:
                raise subprocess.TimeoutExpired(cmd, timeout)
            return subprocess.CompletedProcess(cmd, 1 if sub == "merge-base" else 0,
                                               self.TAGS if sub == "ls-remote" else "", "")

        return mock.patch("afc.update.subprocess.run", side_effect=run)

    def took(self, budget):
        started = time.monotonic()
        result = update.check(self.copy, self.home, now=1_000_000.0, budget=budget)
        return time.monotonic() - started, result

    def test_every_git_call_of_the_look_ends_by_the_one_deadline(self):
        calls = []
        with self.fake_git({"ls-remote": 0.2, "fetch": 0.2}, calls):
            took, result = self.took(budget=1.0)
        self.assertEqual(result, {"update": "none", "current": "v0.01a"})
        self.assertGreaterEqual(len(calls), 3)
        for sub, began, timeout in calls:
            self.assertLessEqual(began + timeout, 1.0 + 0.05, f"{sub} was given time past the deadline")
        self.assertLess(took, 1.0 + 0.3, f"the look took {took:.2f}s of a 1s budget")

    def test_the_tag_loop_is_bounded_by_the_time_left_not_the_whole_budget(self):
        calls = []
        with self.fake_git({"ls-remote": 0.2, "fetch": 0.2}, calls):
            took, _ = self.took(budget=1.0)
        merges = [timeout for sub, _, timeout in calls if sub == "merge-base"]
        self.assertTrue(merges)
        self.assertLess(max(merges), 0.7, "a merge-base call was given the whole budget again")
        self.assertLess(took, 1.0 + 0.3)

    def test_no_git_call_starts_once_the_budget_is_spent(self):
        calls = []
        with self.fake_git({"ls-remote": 0.6, "fetch": 0.6}, calls):
            took, result = self.took(budget=0.5)
        self.assertEqual([sub for sub, _, _ in calls], ["ls-remote"])
        self.assertEqual(result["update"], "none")
        self.assertLess(took, 0.5 + 0.3)

    def test_a_hung_branch_lookup_does_not_come_on_top_of_the_budget(self):
        calls = []
        with self.fake_git({"rev-parse": 9, "ls-remote": 9}, calls):
            took, result = self.took(budget=0.5)
        self.assertEqual(result["update"], "none")
        self.assertLess(took, 0.5 + 0.3, f"the check took {took:.2f}s of a 0.5s budget")


class DeveloperCopyTest(RemoteCase):
    """Whether this is a developer copy is read from the folder, with no git to run or wait for."""

    def is_developer_copy(self, root=None):
        with mock.patch("afc.update.subprocess.run", side_effect=AssertionError("git ran")):
            return update.developer_copy(root or self.copy, self.home)

    def test_a_copy_on_main_is_not(self):
        self.assertFalse(self.is_developer_copy())

    def test_a_copy_on_dev_is(self):
        git(self.copy, "switch", "-qc", "dev")
        self.assertTrue(self.is_developer_copy())

    def test_other_branches_are_not_dev(self):
        for name in ("dev2", "feat/dev", "develop", "devs"):
            with self.subTest(branch=name):
                git(self.copy, "switch", "-qc", name)
                self.assertFalse(self.is_developer_copy())

    def test_a_detached_copy_is_not(self):
        git(self.copy, "checkout", "-q", "--detach")
        self.assertFalse(self.is_developer_copy())

    def test_a_linked_worktree_on_dev_is(self):
        linked = self.tmp / "linked"
        git(self.copy, "worktree", "add", "-q", "-b", "dev", str(linked))
        self.assertTrue((linked / ".git").is_file())
        self.assertTrue(self.is_developer_copy(linked))

    def test_a_folder_that_is_not_a_repository_is_not(self):
        self.assertFalse(self.is_developer_copy(self.tmp / "nowhere"))
        (self.tmp / "plain").mkdir()
        self.assertFalse(self.is_developer_copy(self.tmp / "plain"))

    def test_an_unreadable_head_is_not(self):
        broken = self.tmp / "broken"
        (broken / ".git").mkdir(parents=True)
        (broken / ".git" / "HEAD").write_bytes(b"\xff\xfe\x00 not text")
        self.assertFalse(self.is_developer_copy(broken))

    def test_maintenance_mode_is(self):
        set_maintain(self.home, True)
        self.assertTrue(self.is_developer_copy())


class UpdateOfferAnswerTest(RemoteCase):
    """offer is what the welcome asks: the saved answer, and never a wait for the network."""

    NOW = 1_000_000.0

    def offer(self, now=None):
        with mock.patch("afc.update.subprocess.run", side_effect=AssertionError("git ran")):
            return update.offer(self.copy, self.home, now=self.NOW if now is None else now)

    def saved(self):
        return json.loads((self.home / update.STATE).read_text())

    def test_a_due_day_is_claimed_and_the_look_is_started_once(self):
        self.tag("v0.02a")
        self.assertEqual(self.offer(), {"update": "none", "current": "v0.01a"})
        update.start_refresh.assert_called_once_with(self.copy, self.home, self.NOW)
        self.assertEqual(self.saved(), {"checked_at": self.NOW})
        self.offer(now=self.NOW + 60)
        update.start_refresh.assert_called_once()

    def test_the_look_finds_the_release_and_the_next_offer_has_it(self):
        self.tag("v0.02a")
        self.offer()
        update.refresh(self.copy, self.home, self.NOW)
        self.assertEqual(self.offer(now=self.NOW + 60),
                         {"update": "available", "current": "v0.01a", "latest": "v0.02a"})
        update.start_refresh.assert_called_once()

    def test_a_saved_answer_from_today_is_used_as_it_is(self):
        self.write_state(checked_at=self.NOW - 60, latest="v0.02a")
        self.assertEqual(self.offer()["latest"], "v0.02a")
        update.start_refresh.assert_not_called()

    def test_an_answer_more_than_a_day_old_is_still_offered_while_the_new_look_runs(self):
        self.write_state(checked_at=self.NOW - 3 * DAY, latest="v0.02a")
        self.assertEqual(self.offer()["update"], "available")
        update.start_refresh.assert_called_once()
        self.assertEqual(self.saved()["latest"], "v0.02a")
        self.assertEqual(self.saved()["checked_at"], self.NOW)

    def test_a_skipped_release_stays_skipped_through_the_claim_and_the_look(self):
        self.tag("v0.02a")
        update.skip(self.home, "v0.02a")
        self.offer()
        update.refresh(self.copy, self.home, self.NOW)
        self.assertEqual(self.saved()["skipped"], "v0.02a")
        self.assertEqual(self.offer(now=self.NOW + 60)["update"], "none")

    def test_a_release_skipped_while_the_look_runs_is_not_lost(self):
        self.tag("v0.02a")
        self.offer()
        real_newest = update.remote_newest

        def skipped_meanwhile(*args, **kwargs):
            update.skip(self.home, "v0.02a")
            return real_newest(*args, **kwargs)

        with mock.patch.object(update, "remote_newest", side_effect=skipped_meanwhile):
            update.refresh(self.copy, self.home, self.NOW)
        self.assertEqual(self.saved()["skipped"], "v0.02a")

    def test_a_developer_copy_is_not_looked_at_and_not_claimed(self):
        git(self.copy, "switch", "-qc", "dev")
        self.assertEqual(self.offer()["update"], "none")
        update.start_refresh.assert_not_called()
        self.assertFalse((self.home / update.STATE).exists())

    def test_a_workspace_that_cannot_be_written_starts_no_look(self):
        with mock.patch.object(update, "_save", return_value=False):
            self.assertEqual(self.offer()["update"], "none")
        update.start_refresh.assert_not_called()

    def test_a_missing_version_file_is_an_error_for_the_caller_to_swallow(self):
        (self.copy / "VERSION").unlink()
        with self.assertRaises(update.version.VersionError):
            self.offer()

    def test_the_saved_state_is_written_all_at_once(self):
        self.assertTrue(update._save(self.home, {"checked_at": 1}))
        self.assertEqual(sorted(p.name for p in self.home.iterdir()), [update.STATE])
        blocked = self.tmp / "a-file"
        blocked.write_text("")
        self.assertFalse(update._save(blocked, {"checked_at": 1}))


class BackgroundLookTest(RemoteCase):
    """The look the welcome starts is a process of its own: python -m afc.update."""

    def run_look(self, *argv):
        env = dict(os.environ, PYTHONPATH=str(Path(update.__file__).resolve().parents[1]))
        return subprocess.run([sys.executable, "-m", "afc.update", *map(str, argv)], env=env,
                              cwd=self.tmp, capture_output=True, text=True, timeout=60)

    def test_it_saves_what_origin_says_and_prints_nothing(self):
        self.tag("v0.02a")
        done = self.run_look(self.copy, self.home, 1_000_000.0)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
        self.assertEqual(json.loads((self.home / update.STATE).read_text()),
                         {"checked_at": 1_000_000.0, "latest": "v0.02a"})

    def test_it_says_nothing_and_exits_cleanly_when_the_origin_is_gone(self):
        self.go_offline()
        done = self.run_look(self.copy, self.home, 1_000_000.0)
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
        self.assertNotIn("latest", json.loads((self.home / update.STATE).read_text()))

    def test_bad_arguments_exit_cleanly(self):
        for argv in ((), ("only-one",), (self.copy, self.home, "not-a-time")):
            with self.subTest(argv=argv):
                done = self.run_look(*argv)
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_it_starts_detached_without_a_terminal_or_output(self):
        with mock.patch("afc.update.subprocess.Popen") as popen:
            self.real_start_refresh(self.copy, self.home, 1_000_000.0)
        kwargs = popen.call_args.kwargs
        for stream in ("stdin", "stdout", "stderr"):
            self.assertIs(kwargs[stream], subprocess.DEVNULL)
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(popen.call_args.args[0][1:3], ["-m", "afc.update"])

    def test_a_process_that_cannot_start_is_not_an_error(self):
        with mock.patch("afc.update.subprocess.Popen", side_effect=OSError):
            self.assertIsNone(self.real_start_refresh(self.copy, self.home, 1_000_000.0))
