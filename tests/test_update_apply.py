"""Tests for FC-011 slice 4: the one-click update (update, fast-forward only)."""

import subprocess
from unittest import mock

from afc import update_apply
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
        self.assertIn("v0.01a", out["summary"])
        self.assertIn("Second release", out["summary"])

    def test_long_list_is_cut(self):
        for i in range(12):
            self.commit(f"change {i}")
        git(self.remote, "tag", "-a", "v0.02a", "-m", "Big one")
        out = self.apply()
        self.assertEqual(len(out["changes"]), update_apply.MAX_CHANGES + 1)
        self.assertEqual(out["changes"][-1], "and 4 more")

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

    def test_local_edits_refuse_and_leave_copy_untouched(self):
        self.dirty()
        self.release()
        before = head(self.copy)
        out = self.apply()
        self.assertFalse(out["updated"])
        self.assertIn("local edits", out["reason"])
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
        self.assertIn("not on main", out["reason"])
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
        self.assertIn("newest", out["reason"])

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
