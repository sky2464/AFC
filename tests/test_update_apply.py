"""Tests for FC-011 slice 4: the one-click update (update, fast-forward only)."""

import subprocess
import unittest
from unittest import mock

from afc import update, update_apply
from tests.helpers import RemoteCase, git, run_cli


def head(path):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True).stdout.strip()


class ApplyTest(RemoteCase):
    def release(self, tag="v0.02a", text="v0.02a", message="Second release"):
        self.commit(text)
        git(self.remote, "tag", "-a", tag, "-m", message)

    def dirty(self):
        """Give the copy a tracked file with an uncommitted edit (the release still comes after)."""
        (self.remote / "notes.md").write_text("one\n")
        git(self.remote, "add", "notes.md")
        git(self.remote, "commit", "-qm", "notes")
        git(self.copy, "pull", "-q", "--ff-only")
        (self.copy / "notes.md").write_text("edited\n")

    def apply(self):
        with mock.patch("afc.update_apply.run_check", return_value={"ok": True, "problems": []}) as check:
            self.check_mock = check
            return update_apply.apply(self.copy, self.home)

    def test_fast_forwards_to_newest_tag(self):
        self.release("v0.02a", "v0.02a")
        self.release("v0.10a", "v0.10a", "Tenth release")
        out = self.apply()
        self.assertTrue(out["updated"])
        self.assertEqual((out["from"], out["to"], out["title"]), ("v0.01a", "v0.10a", "Tenth release"))
        self.assertEqual(head(self.copy), head(self.remote))
        self.assertEqual((self.copy / "VERSION").read_text().strip(), "v0.10a")

    def test_summary_lists_what_changed(self):
        self.release("v0.02a", "v0.02a")
        out = self.apply()
        self.assertEqual(out["changes"], ["v0.02a"])
        self.assertEqual(out["title"], "Second release")
        self.assertEqual((out["from"], out["to"]), ("v0.01a", "v0.02a"))
        self.assertTrue(out["summary"])

    def test_long_list_is_cut(self):
        for i in range(12):
            self.commit(f"change {i}")
        git(self.remote, "tag", "-a", "v0.02a", "-m", "Big one")
        out = self.apply()
        self.assertEqual(len(out["changes"]), update_apply.MAX_CHANGES + 1)
        self.assertTrue(out["changes"][-1].startswith("and "))
        self.assertIn(str(12 - update_apply.MAX_CHANGES), out["changes"][-1])

    def test_lightweight_tag_title_falls_back_to_commit_or_tag(self):
        self.commit("v0.02a")
        self.tag("v0.02a")
        out = self.apply()
        self.assertTrue(out["updated"])
        self.assertTrue(out["title"])

    def test_check_runs_after_the_update(self):
        self.release()
        out = self.apply()
        self.check_mock.assert_called_once_with(self.copy)
        self.assertEqual(out["check"], {"ok": True, "problems": []})

    def test_check_is_not_run_when_refused(self):
        self.dirty()
        self.release()
        with mock.patch("afc.update_apply.run_check") as check:
            update_apply.apply(self.copy, self.home)
        check.assert_not_called()

    def test_check_that_cannot_run_is_reported_not_fatal(self):
        self.release()
        out = update_apply.apply(self.copy, self.home)  # the test copy has no bin/afc
        self.assertTrue(out["updated"])
        self.assertIsNone(out["check"])

    def test_failing_check_is_told_in_the_summary(self):
        self.release()
        bad_check = {"ok": False, "problems": [{"kind": "code_missing", "detail": "zzqq folder gone"}]}
        with mock.patch("afc.update_apply.run_check", return_value=bad_check):
            out = update_apply.apply(self.copy, self.home)
        self.assertTrue(out["updated"])
        self.assertEqual(out["check"], bad_check)
        self.assertIn("zzqq folder gone", out["summary"])

    def test_add_ons_are_one_counted_phrase_in_the_summary(self):
        self.release()
        addons = [{"kind": "addon_not_allowed", "addon": f"a{i}@x", "detail": f"a{i}@x isn't allowed."}
                  for i in range(28)]
        with mock.patch("afc.update_apply.run_check", return_value={"ok": False, "problems": addons}):
            out = update_apply.apply(self.copy, self.home)
        self.assertIn("28 add-ons will be off in Flight Control sessions from the next start.", out["summary"])
        self.assertNotIn("a0@x", out["summary"])
        self.assertEqual(out["check"]["problems"], addons)  # the full list stays in the JSON

    def test_fetch_merge_and_log_get_the_long_budget(self):
        self.release()
        seen = {}
        real = subprocess.run

        def spy(cmd, *a, **kw):
            seen[tuple(cmd[1:3])] = kw.get("timeout")
            return real(cmd, *a, **kw)

        with mock.patch("afc.update.subprocess.run", side_effect=spy):
            self.apply()
        for key in (("merge", "--ff-only"), ("log", "--format=%s")):
            self.assertGreater(seen[key], update.TIMEOUT, key)
        self.assertGreater(seen[("fetch", "--quiet")], update.TIMEOUT)

    def test_refused_merge_leaves_no_tag_behind(self):
        self.release()
        (self.copy / "local.txt").write_text("mine")
        git(self.copy, "add", "local.txt")
        git(self.copy, "commit", "-qm", "local work")
        self.assertFalse(self.apply()["updated"])
        tags = subprocess.run(["git", "tag", "-l"], cwd=self.copy, capture_output=True, text=True).stdout
        self.assertNotIn("v0.02a", tags)

    def test_updated_copy_keeps_the_tag(self):
        self.release()
        self.assertTrue(self.apply()["updated"])
        tags = subprocess.run(["git", "tag", "-l"], cwd=self.copy, capture_output=True, text=True).stdout
        self.assertIn("v0.02a", tags)

    def test_local_edits_refuse_and_leave_copy_untouched(self):
        self.dirty()
        self.release()
        before = head(self.copy)
        out = self.apply()
        self.assertFalse(out["updated"])
        self.assertTrue(out["reason"])
        self.assertEqual(head(self.copy), before)
        self.assertEqual((self.copy / "notes.md").read_text(), "edited\n")

    def test_untracked_file_counts_as_not_clean(self):
        self.release()
        (self.copy / "notes.txt").write_text("x")
        self.assertFalse(self.apply()["updated"])
        self.assertTrue((self.copy / "notes.txt").exists())

    def test_other_branch_refuses_untouched(self):
        self.release()
        git(self.copy, "switch", "-q", "-c", "side")
        before = head(self.copy)
        out = self.apply()
        self.assertFalse(out["updated"])
        self.assertTrue(out["reason"])
        self.assertEqual(head(self.copy), before)

    def test_detached_head_refuses(self):
        self.release()
        git(self.copy, "checkout", "-q", "--detach")
        self.assertFalse(self.apply()["updated"])

    def test_dev_branch_refuses(self):
        self.release()
        git(self.copy, "switch", "-q", "-c", "dev")
        self.assertFalse(self.apply()["updated"])

    def test_diverged_copy_is_not_merged_or_forced(self):
        self.release()
        (self.copy / "local.txt").write_text("mine")
        git(self.copy, "add", "local.txt")
        git(self.copy, "commit", "-qm", "local work")
        before = head(self.copy)
        out = self.apply()
        self.assertFalse(out["updated"])
        self.assertEqual(head(self.copy), before)
        parents = subprocess.run(["git", "rev-list", "--merges", "HEAD"], cwd=self.copy, capture_output=True, text=True).stdout
        self.assertEqual(parents.strip(), "")

    def test_already_newest(self):
        out = self.apply()
        self.assertFalse(out["updated"])
        self.assertTrue(out["reason"])
        self.assertNotIn("to", out)

    def test_offline_changes_nothing(self):
        self.release()
        self.go_offline()
        before = head(self.copy)
        out = self.apply()
        self.assertFalse(out["updated"])
        self.assertEqual(head(self.copy), before)

    def test_tag_only_on_dev_is_not_applied(self):
        git(self.remote, "switch", "-q", "-c", "dev")
        self.release("v0.09a", "v0.09a")
        git(self.remote, "switch", "-q", "main")
        before = head(self.copy)
        out = self.apply()
        self.assertFalse(out["updated"])
        self.assertEqual(head(self.copy), before)

    def test_every_git_call_is_quiet_and_never_forced(self):
        self.release()
        calls = []
        real = update_apply.update._git

        def spy(root, *args, **kw):
            calls.append(args)
            return real(root, *args, **kw)

        with mock.patch("afc.update._git", side_effect=spy):
            self.apply()
        flat = [a for c in calls for a in c]
        self.assertIn("--ff-only", flat)
        for bad in ("--force", "-f", "--hard", "reset", "rebase", "push"):
            self.assertNotIn(bad, flat)

    def test_command_updates(self):
        self.release()
        with mock.patch("afc.cli_version.afc_root", return_value=self.copy), mock.patch(
            "afc.update_apply.run_check", return_value={"ok": True, "problems": []}
        ):
            code, out = run_cli(["update"])
        self.assertEqual((code, out["updated"], out["to"]), (0, True, "v0.02a"))

    def test_command_refusal_is_one_object_with_a_reason(self):
        self.dirty()
        self.release()
        with mock.patch("afc.cli_version.afc_root", return_value=self.copy):
            code, out = run_cli(["update"])
        self.assertEqual((code, out["updated"]), (0, False))
        self.assertTrue(out["reason"])


if __name__ == "__main__":
    import unittest

    unittest.main()


class CheckSentenceTest(unittest.TestCase):
    """What the update summary says about the health check: one sentence, never a list."""

    ADDONS = [{"kind": "addon_not_allowed", "detail": f"a{i}@x isn't allowed."} for i in range(3)]
    GONE = {"kind": "code_missing", "detail": "demo: its code folder is gone. If it moved, relocate it."}
    EMPTY = {"kind": "architecture_empty", "detail": "demo: architecture.md is empty."}

    def sentence(self, problems):
        return update_apply.check_sentence({"ok": not problems, "problems": problems})

    def sentences(self, text):
        return [s for s in text.replace("? ", ". ").split(". ") if s.strip()]

    def test_a_clean_check(self):
        self.assertEqual(self.sentence([]), "Everything checks out.")

    def test_no_check_says_nothing(self):
        self.assertEqual(update_apply.check_sentence(None), "")

    def test_add_ons_only(self):
        self.assertEqual(self.sentence(self.ADDONS),
                         "3 add-ons will be off in Flight Control sessions from the next start.")
        one = update_apply.check_sentence({"ok": False, "problems": self.ADDONS[:1]})
        self.assertEqual(one, "1 add-on will be off in Flight Control sessions from the next start.")

    def test_other_problems_show_the_first_and_count_the_rest(self):
        text = self.sentence([self.GONE, self.EMPTY, *self.ADDONS])
        self.assertEqual(text, "2 things need a look, first: demo: its code folder is gone, and 1 more; "
                               "3 add-ons will be off in Flight Control sessions from the next start.")
        self.assertEqual(len(self.sentences(text)), 1)

    def test_one_other_problem(self):
        self.assertEqual(self.sentence([self.EMPTY]), "1 thing needs a look: demo: architecture.md is empty.")
