"""Maintenance mode with no session ID follows the copy's branch (FC-051 slice 4)."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from afc import cli, config
from afc.hooks import pretool

OWN_FILE = str(config.afc_root() / "afc" / "config.py")


class BranchMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-mb-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"AFC_HOME": str(self.tmp)})
        env.start()
        self.addCleanup(env.stop)
        for name in ("CLAUDE_CODE_SESSION_ID", "AFC_SESSION", "CURSOR_CONVERSATION_ID"):
            os.environ.pop(name, None)
        self.branch = "feature/x"
        for target, value in (("afc.update._branch", lambda root: self.branch),):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return code, json.loads(out.getvalue())

    def test_on_and_off_without_a_session_id(self):
        status = self.run_cli("maintain")[1]
        self.assertEqual(status["maintain"], False)
        self.assertEqual(status["scope"], "off")
        code, result = self.run_cli("maintain", "on")
        self.assertEqual(code, 0)
        self.assertEqual(result["maintain"], True)
        self.assertEqual(result["scope"], "branch")
        self.assertIn("branch", result.get("applies", ""))
        self.assertEqual(self.run_cli("maintain", "status")[1]["scope"], "branch")
        off = self.run_cli("maintain", "off")[1]
        self.assertEqual(off["maintain"], False)
        self.assertEqual(off["scope"], "off")

    def test_it_is_per_branch(self):
        self.run_cli("maintain", "on")
        self.branch = "other"
        self.assertEqual(self.run_cli("maintain")[1]["scope"], "off")

    def test_never_on_for_main(self):
        self.branch = "main"
        code, result = self.run_cli("maintain", "on")
        self.assertEqual(code, 1)
        self.assertIn("error", result)
        self.assertEqual(self.run_cli("maintain")[1]["scope"], "off")

    def test_detached_head_cannot_turn_it_on(self):
        self.branch = ""
        code, result = self.run_cli("maintain", "on")
        self.assertEqual(code, 1)
        self.assertIn("branch", result["error"])

    def test_a_session_id_ignores_the_branch_switch(self):
        self.run_cli("maintain", "on")
        self.assertEqual(config.maintain_scope(config.afc_home(), "sess1"), "off")
        config.set_maintain(config.afc_home(), True, "sess1")
        self.assertEqual(config.maintain_scope(config.afc_home(), "sess1"), "session")
        self.assertEqual(config.maintain_scope(config.afc_home(), None), "branch")

    def test_cursor_conversation_falls_back_to_branch(self):
        # FC-054: Cursor Write sees CURSOR_CONVERSATION_ID; branch /afc mm must still apply.
        self.run_cli("maintain", "on")
        os.environ["CURSOR_CONVERSATION_ID"] = "cursor-chat-1"
        self.addCleanup(os.environ.pop, "CURSOR_CONVERSATION_ID", None)
        self.assertEqual(config.current_session(), "cursor-chat-1")
        self.assertEqual(config.maintain_scope(config.afc_home(), "cursor-chat-1"), "branch")
        self.assertTrue(config.maintain_enabled(config.afc_home(), "cursor-chat-1"))

    def test_cursor_mm_on_sets_branch_not_session(self):
        os.environ["CURSOR_CONVERSATION_ID"] = "cursor-chat-2"
        self.addCleanup(os.environ.pop, "CURSOR_CONVERSATION_ID", None)
        code, result = self.run_cli("maintain", "on")
        self.assertEqual(code, 0)
        self.assertEqual(result["scope"], "branch")
        self.assertIn("branch", result["applies"])
        self.assertFalse((config.afc_home() / "maintain.d" / "cursor-chat-2").exists())

    def test_stale_afc_session_does_not_hide_cursor_branch(self):
        # FC-054: a leftover AFC_SESSION must not make branch /afc mm look off in Cursor.
        self.run_cli("maintain", "on")
        os.environ["AFC_SESSION"] = "stale-parent"
        os.environ["CURSOR_CONVERSATION_ID"] = "cursor-chat-3"
        self.addCleanup(os.environ.pop, "AFC_SESSION", None)
        self.addCleanup(os.environ.pop, "CURSOR_CONVERSATION_ID", None)
        self.assertEqual(config.current_session(), "cursor-chat-3")
        self.assertEqual(self.run_cli("maintain", "status")[1]["scope"], "branch")
        self.assertTrue(config.maintain_enabled(config.afc_home(), config.current_session()))

    def test_stale_afc_session_maintain_off_clears_branch(self):
        self.run_cli("maintain", "on")
        os.environ["AFC_SESSION"] = "stale-parent"
        os.environ["CURSOR_CONVERSATION_ID"] = "cursor-chat-4"
        self.addCleanup(os.environ.pop, "AFC_SESSION", None)
        self.addCleanup(os.environ.pop, "CURSOR_CONVERSATION_ID", None)
        off = self.run_cli("maintain", "off")[1]
        self.assertEqual(off["scope"], "off")
        os.environ.pop("AFC_SESSION", None)
        self.assertEqual(self.run_cli("maintain", "status")[1]["scope"], "off")


    def edit(self, **fields):
        """Exit code of the Claude Code edit guard for a write to a Flight Control file."""
        event = {"tool_name": "Write", "tool_input": {"file_path": OWN_FILE, "content": "x"},
                 "cwd": str(config.afc_root()), **fields}
        return pretool.main(json.dumps(event), io.StringIO())

    def test_cursor_edit_through_the_claude_hook_sees_the_branch_switch(self):
        # FC-057: Cursor runs the Claude Code edit guard but sets no CURSOR_CONVERSATION_ID;
        # its own fields in the message must still mark the chat as Cursor's.
        self.run_cli("maintain", "on")
        self.assertEqual(self.edit(session_id="cursor-chat-5", cursor_version="2.1.0"), 0)
        self.assertEqual(self.edit(conversation_id="cursor-chat-6", cursor_version="2.1.0"), 0)
        self.assertEqual(self.edit(conversation_id="cursor-chat-7"), 0)

    def test_cursor_edit_is_still_blocked_with_the_branch_switch_off(self):
        self.assertEqual(self.edit(conversation_id="cursor-chat-8", cursor_version="2.1.0"), 2)

    def test_a_claude_edit_still_ignores_the_branch_switch(self):
        self.run_cli("maintain", "on")
        self.assertEqual(self.edit(session_id="claude-sess-1"), 2)


if __name__ == "__main__":
    unittest.main()
