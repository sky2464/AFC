"""Per-session maintenance mode: the switch, the command, the guard and the saved session ID."""

import io
import json
import os
import time
from pathlib import Path
from unittest.mock import patch

from afc import config
from afc.hooks.common import Context, load_context, policy_reason
from afc.hooks.session_start import main as session_start_main
from tests.helpers import AfcTestCase, run_cli
from tests.test_cli import CliTestCase

A, B = "11111111-aaaa-bbbb-cccc-000000000001", "22222222-aaaa-bbbb-cccc-000000000002"
NO_SESSION = {"AFC_SESSION": "", "CLAUDE_CODE_SESSION_ID": ""}


class MaintainConfigTest(AfcTestCase):
    def test_on_for_one_session_leaves_others_off(self):
        config.set_maintain(self.home, True, A)
        self.assertTrue(config.maintain_enabled(self.home, A))
        self.assertFalse(config.maintain_enabled(self.home, B))
        self.assertFalse(config.maintain_enabled(self.home, None))

    def test_off_removes_only_that_session(self):
        config.set_maintain(self.home, True, A)
        config.set_maintain(self.home, True, B)
        config.set_maintain(self.home, False, A)
        self.assertEqual(config.maintain_scope(self.home, A), "off")
        self.assertEqual(config.maintain_scope(self.home, B), "session")

    def test_global_switch_still_works_without_a_session(self):
        config.set_maintain(self.home, True, None)
        self.assertEqual(config.maintain_scope(self.home, None), "global")
        self.assertEqual(config.maintain_scope(self.home, A), "global")
        config.set_maintain(self.home, False, None)
        self.assertFalse(config.maintain_enabled(self.home, A))

    def test_off_in_a_session_also_clears_the_global_switch(self):
        config.set_maintain(self.home, True, None)
        config.set_maintain(self.home, True, A)
        config.set_maintain(self.home, False, A)
        self.assertEqual(config.maintain_scope(self.home, A), "off")

    def test_unsafe_session_ids_are_ignored(self):
        for bad in ("../evil", "a/b", "", "x" * 200, "has space"):
            self.assertIsNone(config.valid_session(bad))
        self.assertEqual(config.valid_session(A), A)
        config.set_maintain(self.home, True, "../evil")
        self.assertEqual(config.maintain_scope(self.home, None), "global")

    def test_old_session_flags_are_pruned_when_turning_on(self):
        config.set_maintain(self.home, True, A)
        old = self.home / "maintain.d" / A
        week_ago = time.time() - 8 * 86400
        os.utime(old, (week_ago, week_ago))
        config.set_maintain(self.home, True, B)
        self.assertFalse(old.exists())
        self.assertTrue(config.maintain_enabled(self.home, B))

    def test_session_comes_from_the_saved_value_first(self):
        env = {"AFC_SESSION": A, "CLAUDE_CODE_SESSION_ID": B}
        with patch.dict(os.environ, env):
            self.assertEqual(config.current_session(), A)
        with patch.dict(os.environ, {"AFC_SESSION": "", "CLAUDE_CODE_SESSION_ID": B}):
            self.assertEqual(config.current_session(), B)
        with patch.dict(os.environ, NO_SESSION):
            self.assertIsNone(config.current_session())


class MaintainCommandTest(CliTestCase):
    def maintain(self, state: str, session: str | None):
        env = {"AFC_SESSION": session or "", "CLAUDE_CODE_SESSION_ID": ""}
        with patch.dict(os.environ, env):
            return run_cli(["maintain", state])

    def test_on_and_off_in_a_session(self):
        self.assertEqual(self.maintain("status", A), (0, {"maintain": False, "scope": "off"}))
        self.assertEqual(self.maintain("on", A), (0, {"maintain": True, "scope": "session"}))
        self.assertEqual(self.maintain("status", B), (0, {"maintain": False, "scope": "off"}))
        self.assertEqual(self.maintain("off", A), (0, {"maintain": False, "scope": "off"}))

    def test_without_a_session_it_is_global_and_says_so(self):
        rc, out = self.maintain("on", None)
        self.assertEqual((rc, out["scope"]), (0, "global"))
        self.assertIn("every session", out["note"])
        self.assertEqual(self.maintain("status", A)[1]["scope"], "global")

    def test_no_state_names_on_off_and_status(self):
        rc, out = run_cli(["maintain"])
        self.assertNotEqual(rc, 0)
        for word in ("on", "off", "status"):
            self.assertIn(word, out["error"])


class MaintainGuardTest(AfcTestCase):
    def test_load_context_uses_the_event_session(self):
        config.set_maintain(self.home, True, A)
        self.assertTrue(load_context(A).maintain)
        self.assertFalse(load_context(B).maintain)
        self.assertFalse(load_context(None).maintain)

    def test_session_flag_files_cannot_be_written_through_the_guard(self):
        ctx = Context(home=self.home, root=Path("/nowhere"), active=None, maintain=True)
        for target in (self.home / "maintain.d", self.home / "maintain.d" / A):
            self.assertIn("can't be changed", policy_reason(target.resolve(), ctx) or "")

    def test_pretool_passes_the_event_session_to_the_context(self):
        from afc.hooks import pretool

        seen = []
        with patch.object(pretool, "load_context", side_effect=lambda s=None: seen.append(s)):
            pretool.main(json.dumps({"tool_name": "Write", "session_id": A,
                                     "tool_input": {"file_path": "/x"}}), io.StringIO())
        self.assertEqual(seen, [A])


class SessionStartSavesTheSessionTest(AfcTestCase):
    def run_hook(self, stdin_text: str, env_file: Path | None) -> int:
        env = {"CLAUDE_ENV_FILE": str(env_file)} if env_file else {"CLAUDE_ENV_FILE": ""}
        with patch.dict(os.environ, env):
            return session_start_main(io.StringIO(), stdin_text)

    def test_saves_the_session_id_for_later_commands(self):
        env_file = self.tmp / "env.sh"
        rc = self.run_hook(json.dumps({"session_id": A}), env_file)
        self.assertEqual(rc, 0)
        self.assertEqual(env_file.read_text(), f"export AFC_SESSION={A}\n")

    def test_appends_so_the_latest_session_wins(self):
        env_file = self.tmp / "env.sh"
        env_file.write_text("export OTHER=1\n")
        self.run_hook(json.dumps({"session_id": A}), env_file)
        self.assertEqual(env_file.read_text(), f"export OTHER=1\nexport AFC_SESSION={A}\n")

    def test_never_breaks_the_welcome(self):
        for text in ("", "not json", json.dumps({"session_id": "../evil"}), json.dumps([1])):
            self.assertEqual(self.run_hook(text, self.tmp / "env.sh"), 0)
        self.assertFalse((self.tmp / "env.sh").exists())
        self.assertEqual(self.run_hook(json.dumps({"session_id": A}), None), 0)
