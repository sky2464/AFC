"""Tests for FC-011 slice 2: checking for a newer release (update --check)."""

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from afc import update
from afc.config import set_maintain
from tests.helpers import AfcTestCase, run_cli

DAY = 86400


def git(cwd, *args, **extra_env):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, **extra_env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main", *args],
        cwd=cwd, check=True, capture_output=True, env=env,
    )


class RemoteCase(AfcTestCase):
    """A test remote on main with one release (v0.01a), and a clone of it as the Flight Control copy."""

    def setUp(self):
        super().setUp()
        self.remote = self.tmp / "remote"
        self.remote.mkdir()
        git(self.remote, "init", "-q")
        (self.remote / "VERSION").write_text("v0.01a\n")
        git(self.remote, "add", "VERSION")
        git(self.remote, "commit", "-qm", "one")
        git(self.remote, "tag", "v0.01a")
        self.copy = self.tmp / "copy"
        git(self.tmp, "clone", "-q", str(self.remote), str(self.copy))

    def tag(self, *names):
        for name in names:
            git(self.remote, "tag", name)

    def commit(self, text, date=None):
        (self.remote / "VERSION").write_text(text + "\n")
        when = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date} if date else {}
        git(self.remote, "commit", "-qam", text, **when)

    def write_state(self, **data):
        (self.home / update.STATE).write_text(json.dumps(data), encoding="utf-8")

    def go_offline(self):
        git(self.copy, "remote", "set-url", "origin", str(self.tmp / "gone"))

    def check(self, now=1_000_000.0):
        return update.check(self.copy, self.home, now=now)


class UpdateCheckTest(RemoteCase):
    def test_newer_tag_is_offered(self):
        self.tag("v0.02a")
        self.assertEqual(self.check(), {"update": "available", "current": "v0.01a", "latest": "v0.02a"})

    def test_newest_tag_is_offered(self):
        self.tag("v0.10a", "v0.09a")
        self.assertEqual(self.check()["latest"], "v0.10a")

    def test_version_order_is_numeric_not_text(self):
        # as text v9.0a > v10.0a and v0.9a > v0.10a; as versions it is the other way round
        self.tag("v0.9a", "v0.10a", "v9.0a", "v10.0a")
        self.assertEqual(self.check()["latest"], "v10.0a")
        self.tag("v0.11a")
        self.assertEqual(self.check(now=1_000_000.0 + 2 * DAY)["latest"], "v10.0a")

    def test_installed_version_is_compared_numerically(self):
        # as text v0.10a < v0.9a, so a text comparison would call v0.10a old
        (self.copy / "VERSION").write_text("v0.9a\n")
        self.tag("v0.10a")
        self.assertEqual(self.check(), {"update": "available", "current": "v0.9a", "latest": "v0.10a"})

    def test_older_tag_is_not_offered_even_if_it_sorts_higher_as_text(self):
        (self.copy / "VERSION").write_text("v0.10a\n")
        self.tag("v0.9a")
        self.assertEqual(self.check(), {"update": "none", "current": "v0.10a"})

    def test_skipped_version_is_compared_numerically(self):
        self.tag("v0.10a")
        update.skip(self.home, "v0.9a")
        self.assertEqual(self.check()["latest"], "v0.10a")

    def test_version_order_beats_commit_order(self):
        # the higher version sits on an older main commit than the lower one
        self.commit("two", date="2026-01-02T00:00:00")
        self.tag("v0.10a")
        self.commit("three", date="2026-01-03T00:00:00")
        self.tag("v0.02a")
        self.assertEqual(self.check()["latest"], "v0.10a")

    def test_version_order_beats_commit_and_listing_order(self):
        # git lists tags as text: v0.10a comes before v0.9a, and v0.9a is on the newest commit
        self.commit("two", date="2026-01-02T00:00:00")
        self.tag("v0.10a")
        self.commit("three", date="2026-01-03T00:00:00")
        self.tag("v0.9a")
        self.assertEqual(self.check()["latest"], "v0.10a")

    def test_version_order_beats_annotated_tag_date(self):
        self.commit("two")
        git(self.remote, "tag", "-a", "v0.10a", "-m", "old", GIT_COMMITTER_DATE="2026-01-01T00:00:00")
        self.commit("three")
        git(self.remote, "tag", "-a", "v0.02a", "-m", "new", GIT_COMMITTER_DATE="2026-06-01T00:00:00")
        self.assertEqual(self.check()["latest"], "v0.10a")

    def test_only_v_tags_count(self):
        self.tag("release-9", "v9-beta", "nightly")
        self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})

    def test_no_newer_tag(self):
        self.assertEqual(self.check()["update"], "none")

    def test_offline_says_nothing(self):
        git(self.copy, "remote", "set-url", "origin", str(self.tmp / "gone"))
        self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})

    def test_short_timeout_counts_as_offline(self):
        def slow(*a, **k):
            raise subprocess.TimeoutExpired(a[0], k.get("timeout"))

        with mock.patch("afc.update.subprocess.run", side_effect=slow) as run:
            self.assertEqual(self.check()["update"], "none")
        self.assertLessEqual(run.call_args.kwargs["timeout"], update.TIMEOUT)
        self.assertLessEqual(update.TIMEOUT, 5)

    def test_runs_at_most_once_a_day(self):
        self.check(now=1_000_000.0)
        self.tag("v0.02a")
        self.assertEqual(self.check(now=1_000_000.0 + DAY - 60)["update"], "none")
        self.assertEqual(self.check(now=1_000_000.0 + DAY + 60)["latest"], "v0.02a")

    def test_cached_result_is_reused(self):
        self.tag("v0.02a")
        self.check()
        stored = json.loads((self.home / update.STATE).read_text())
        self.assertEqual(stored["latest"], "v0.02a")
        git(self.copy, "remote", "set-url", "origin", str(self.tmp / "gone"))
        self.assertEqual(self.check(now=1_000_100.0)["latest"], "v0.02a")

    def test_failed_recheck_after_a_good_one_says_nothing(self):
        self.tag("v0.02a")
        self.assertEqual(self.check(now=1_000_000.0)["latest"], "v0.02a")
        self.go_offline()
        self.assertEqual(self.check(now=1_000_000.0 + DAY + 60), {"update": "none", "current": "v0.01a"})

    def test_timed_out_recheck_after_a_good_one_says_nothing(self):
        self.tag("v0.02a")
        self.assertEqual(self.check(now=1_000_000.0)["update"], "available")

        def slow(*a, **k):
            raise subprocess.TimeoutExpired(a[0], k.get("timeout"))

        with mock.patch("afc.update.subprocess.run", side_effect=slow):
            self.assertEqual(self.check(now=1_000_000.0 + DAY + 60)["update"], "none")

    def test_stale_cache_with_unreachable_origin_says_nothing(self):
        self.write_state(checked_at=1_000_000.0 - 3 * DAY, latest="v0.11a")
        self.go_offline()
        self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})

    def test_failed_recheck_is_not_repeated_until_the_next_day(self):
        self.tag("v0.02a")
        self.check(now=1_000_000.0)
        self.go_offline()
        self.check(now=1_000_000.0 + DAY + 60)
        git(self.copy, "remote", "set-url", "origin", str(self.remote))
        self.assertEqual(self.check(now=1_000_000.0 + DAY + 120)["update"], "none")
        self.assertEqual(self.check(now=1_000_000.0 + 2 * DAY + 120)["latest"], "v0.02a")

    def test_release_removed_from_the_remote_is_not_offered_again(self):
        self.tag("v0.02a")
        self.assertEqual(self.check(now=1_000_000.0)["latest"], "v0.02a")
        git(self.remote, "tag", "-d", "v0.01a", "v0.02a")
        self.assertEqual(self.check(now=1_000_000.0 + DAY + 60)["update"], "none")

    def test_skipped_release_stays_quiet(self):
        self.tag("v0.02a")
        update.skip(self.home, "v0.02a")
        self.assertEqual(self.check()["update"], "none")
        self.tag("v0.03a")
        self.assertEqual(self.check(now=1_000_000.0 + 2 * DAY)["latest"], "v0.03a")

    def test_wrong_typed_update_file_says_nothing_and_does_not_crash(self):
        junk = (5, 1.5, True, ["v0.02a"], {"a": 1}, "banana", None)
        for value in junk:
            with self.subTest(latest=value):
                self.write_state(checked_at=1_000_000.0, latest=value)
                self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})
            with self.subTest(skipped=value):
                self.write_state(checked_at=1_000_000.0, latest="v0.02a", skipped=value)
                self.assertEqual(self.check()["latest"], "v0.02a")
            with self.subTest(checked_at=value):
                self.write_state(checked_at=value, latest="v0.02a", skipped=value)
                self.assertEqual(self.check()["update"], "none")

    def test_wrong_typed_update_file_is_replaced_by_a_fresh_check(self):
        self.tag("v0.02a")
        self.write_state(checked_at=1_000_000.0 - 3 * DAY, latest=5, skipped=["x"])
        self.assertEqual(self.check()["latest"], "v0.02a")
        self.assertEqual(json.loads((self.home / update.STATE).read_text())["latest"], "v0.02a")

    def test_developer_copy_on_dev_never_offers(self):
        self.tag("v0.02a")
        git(self.copy, "switch", "-qc", "dev")
        self.assertEqual(self.check()["update"], "none")

    def test_maintenance_mode_never_offers(self):
        self.tag("v0.02a")
        set_maintain(self.home, True)
        self.assertEqual(self.check()["update"], "none")


    def test_tag_only_on_dev_is_not_offered(self):
        git(self.remote, "switch", "-qc", "dev")
        self.commit("dev work")
        self.tag("v0.03a")
        git(self.remote, "switch", "-q", "main")
        self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})

    def test_annotated_tag_only_on_dev_is_not_offered(self):
        git(self.remote, "switch", "-qc", "dev")
        self.commit("dev work")
        git(self.remote, "tag", "-a", "v0.03a", "-m", "not a release")
        git(self.remote, "switch", "-q", "main")
        self.assertEqual(self.check()["update"], "none")

    def test_tag_on_dev_does_not_hide_the_newest_tag_on_main(self):
        self.commit("two")
        self.tag("v0.02a")
        git(self.remote, "switch", "-qc", "dev")
        self.commit("dev work")
        self.tag("v0.03a")
        git(self.remote, "switch", "-q", "main")
        self.assertEqual(self.check(), {"update": "available", "current": "v0.01a", "latest": "v0.02a"})

    def test_tag_on_an_earlier_main_commit_is_offered(self):
        self.commit("two")
        self.tag("v0.02a")
        self.commit("three")
        self.commit("four")
        self.assertEqual(self.check()["latest"], "v0.02a")

    def test_annotated_tag_on_main_is_offered(self):
        self.commit("two")
        git(self.remote, "tag", "-a", "v0.02a", "-m", "release")
        self.commit("three")
        self.assertEqual(self.check()["latest"], "v0.02a")

    def test_main_missing_on_remote_says_nothing(self):
        git(self.remote, "switch", "-qc", "trunk")
        git(self.remote, "branch", "-qD", "main")
        self.tag("v0.02a")
        self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})

    def test_check_does_not_prompt_for_credentials(self):
        # The git calls must run without a terminal or a credential helper prompt, even for a
        # private origin; here the origin refuses with 401 and a fake askpass records any ask.
        class Refuse(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="private"')
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Refuse)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        asked = self.tmp / "asked"
        askpass = self.tmp / "askpass.sh"
        askpass.write_text(f'#!/bin/sh\ntouch "{asked}"\necho nope\n')
        askpass.chmod(0o755)
        git(self.copy, "remote", "set-url", "origin", f"http://127.0.0.1:{server.server_port}/private.git")
        with mock.patch.dict(os.environ, {"GIT_ASKPASS": str(askpass), "GIT_TERMINAL_PROMPT": "1"}):
            self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})
        self.assertFalse(asked.exists(), "the check asked for a credential")

    def test_git_runs_without_stdin_or_prompts(self):
        with mock.patch("afc.update.subprocess.run", side_effect=OSError) as run:
            self.check()
        self.assertTrue(run.call_args_list)
        for call in run.call_args_list:
            self.assertIs(call.kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(call.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")


class UpdateCommandTest(RemoteCase):
    def test_command_prints_one_object(self):
        self.tag("v0.02a")
        with mock.patch("afc.cli_version.afc_root", return_value=self.copy):
            code, out = run_cli(["update", "--check"])
        self.assertEqual((code, out["update"], out["latest"]), (0, "available", "v0.02a"))

    def test_command_skip(self):
        self.tag("v0.02a")
        with mock.patch("afc.cli_version.afc_root", return_value=self.copy):
            code, out = run_cli(["update", "--skip", "v0.02a"])
            self.assertEqual((code, out), (0, {"skipped": "v0.02a"}))
            code, out = run_cli(["update", "--check"])
        self.assertEqual(out["update"], "none")

    def test_command_with_wrong_typed_update_file_prints_an_object(self):
        import time

        for state in ({"latest": 5}, {"latest": "v0.02a", "skipped": ["x"]}, {"latest": ["v0.02a"], "skipped": 7}):
            with self.subTest(state=state):
                self.write_state(checked_at=time.time(), **state)
                with mock.patch("afc.cli_version.afc_root", return_value=self.copy):
                    code, out = run_cli(["update", "--check"])
                self.assertEqual(code, 0)
                self.assertEqual(out["update"], "available" if state["latest"] == "v0.02a" else "none")

    def test_command_with_stale_cache_and_no_network_says_nothing(self):
        self.write_state(checked_at=1_000_000.0, latest="v0.11a")
        self.go_offline()
        with mock.patch("afc.cli_version.afc_root", return_value=self.copy):
            code, out = run_cli(["update", "--check"])
        self.assertEqual((code, out), (0, {"update": "none", "current": "v0.01a"}))

    def test_bad_skip_is_an_error(self):
        code, out = run_cli(["update", "--skip", "banana"])
        self.assertNotEqual(code, 0)
        self.assertIn("error", out)


if __name__ == "__main__":
    import unittest

    unittest.main()
