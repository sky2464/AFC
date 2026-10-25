"""Tests for FC-011 slice 6: restart only for session-start files; the one-time 'just updated' note."""

from unittest import mock

from afc import update_apply
from afc.hooks import session_start
from afc.hooks.session_start import build_output
from tests.helpers import RemoteCase, git


class RestartTest(RemoteCase):
    def release(self, files, tag="v0.02a"):
        for name in files:
            path = self.remote / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("changed\n")
            git(self.remote, "add", name)
        self.commit(tag)
        git(self.remote, "tag", "-a", tag, "-m", "Second")

    def apply(self):
        with mock.patch("afc.update_apply.run_check", return_value={"ok": True, "problems": []}), \
                mock.patch("afc.update_apply.run_upgrade", return_value={"summary": ""}):
            return update_apply.apply(self.copy, self.home)

    def test_restart_for_each_session_start_file(self):
        for name in ("CLAUDE.md", ".claude/skills/x/SKILL.md", ".claude/commands/afc.md",
                     ".claude/settings.json", "afc/hooks/session_start.py"):
            self.assertTrue(update_apply.needs_restart([name]), name)

    def test_no_restart_for_other_files(self):
        self.assertFalse(update_apply.needs_restart(["README.md", "afc/update.py", "tests/a.py", "VERSION"]))
        self.assertFalse(update_apply.needs_restart([]))

    def test_update_that_changes_claude_md_asks_restart(self):
        self.release(["CLAUDE.md"])
        out = self.apply()
        self.assertTrue(out["restart"])
        self.assertIn("/exit", out["restart_how"])
        self.assertIn("claude --continue", out["restart_how"])

    def test_update_without_those_files_needs_no_restart(self):
        self.release(["docs/notes.md"])
        out = self.apply()
        self.assertTrue(out["updated"])
        self.assertFalse(out["restart"])
        self.assertNotIn("restart_how", out)

    def test_refused_update_leaves_no_note(self):
        self.apply()  # nothing newer
        self.assertFalse((self.home / update_apply.NOTE).exists())


class JustUpdatedTest(RemoteCase):
    def setUp(self):
        super().setUp()
        for name, value in (("afc_root", self.copy), ("_health_line", "")):
            patcher = mock.patch.object(session_start, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_note_shown_once_then_removed(self):
        update_apply.leave_note(self.home, "v0.01a")
        first = build_output(self.home, now=1.0)["systemMessage"]
        self.assertIn("You're on v0.01a now.", first)
        self.assertFalse((self.home / update_apply.NOTE).exists())
        self.assertNotIn("You're on", build_output(self.home, now=2.0)["systemMessage"])

    def test_note_for_other_version_is_dropped_silently(self):
        update_apply.leave_note(self.home, "v0.09a")
        self.assertNotIn("You're on", build_output(self.home, now=1.0)["systemMessage"])
        self.assertFalse((self.home / update_apply.NOTE).exists())

    def test_broken_note_is_removed_and_ignored(self):
        (self.home / update_apply.NOTE).write_text("not json")
        self.assertNotIn("You're on", build_output(self.home, now=1.0)["systemMessage"])
        self.assertFalse((self.home / update_apply.NOTE).exists())
