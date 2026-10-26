"""Hook adapters for Cursor, Codex, Copilot and Antigravity (FC-051 slice 6)."""

import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from afc.config import afc_root
from afc.hooks import adapter

ROOT = afc_root()
OWN_FILE = str(ROOT / "afc" / "config.py")
PUSH = "git push --force"


def payloads(command=None, path=None):
    """The same action as each tool sends it: a shell command, or a write to one file."""
    if command:
        return {
            "cursor": {"hook_event_name": "beforeShellExecution", "command": command, "cwd": "/tmp"},
            "codex": {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": "/tmp"},
            "copilot": {"toolName": "bash", "toolArgs": json.dumps({"command": command}), "cwd": "/tmp"},
            "antigravity": {"toolCall": {"name": "run_command", "args": {"CommandLine": command, "Cwd": "/tmp"}}},
        }
    return {  # cursor has no hook before an edit, so it is not here
        "codex": {"tool_name": "apply_patch", "tool_input": {"command": f"*** Begin Patch\n*** Update File: {path}\n@@\n-a\n+b\n*** End Patch"}, "cwd": "/tmp"},
        "copilot": {"toolName": "edit", "toolArgs": {"path": path, "new_str": "b"}, "cwd": "/tmp"},
        "antigravity": {"toolCall": {"name": "replace_file_content", "args": {"TargetFile": path, "ReplacementContent": "b"}}, "workspacePaths": ["/tmp"]},
    }


def blocked(tool, out, err, code):
    if tool == "cursor":
        return code == 2 and json.loads(out)["permission"] == "deny"
    if tool == "codex":
        return code == 2 and "Flight Control blocked" in err
    if tool == "copilot":
        return json.loads(out)["permissionDecision"] == "deny"
    return json.loads(out).get("decision") == "deny"


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-adapt-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"AFC_HOME": str(self.tmp)})
        env.start()
        self.addCleanup(env.stop)
        for name in ("CLAUDE_CODE_SESSION_ID", "AFC_SESSION"):
            os.environ.pop(name, None)

    def ask(self, tool, payload):
        out, err = io.StringIO(), io.StringIO()
        code = adapter.run(tool, json.dumps(payload), out, err)
        return out.getvalue().strip(), err.getvalue().strip(), code

    def test_a_risky_command_is_blocked_in_every_tool(self):
        for tool, payload in payloads(command=PUSH).items():
            with self.subTest(tool=tool):
                self.assertTrue(blocked(tool, *self.ask(tool, payload)))

    def test_a_harmless_command_is_allowed_in_every_tool(self):
        for tool, payload in payloads(command="ls").items():
            with self.subTest(tool=tool):
                out, err, code = self.ask(tool, payload)
                self.assertEqual((code, err), (0, ""))
                self.assertFalse(blocked(tool, out, err, code))

    def test_editing_flight_control_is_blocked_without_maintenance_mode(self):
        for tool, payload in payloads(path=OWN_FILE).items():
            with self.subTest(tool=tool):
                self.assertTrue(blocked(tool, *self.ask(tool, payload)))

    def test_unreadable_input_blocks_the_tools_that_use_exit_codes(self):
        for tool in ("cursor", "codex"):
            with self.subTest(tool=tool):
                code = adapter.run(tool, "not json", io.StringIO(), io.StringIO())
                self.assertEqual(code, 2)

    def test_a_tool_that_replies_in_json_denies_garbage(self):
        for tool in ("copilot", "antigravity"):
            out = io.StringIO()
            adapter.run(tool, "not json", out, io.StringIO())
            self.assertIn("deny", out.getvalue())

    def test_the_hook_files_call_the_adapters(self):
        wanted = {".cursor/hooks.json": "cursor", ".codex/hooks.json": "codex",
                  ".github/hooks/flight-control.json": "copilot", ".agents/hooks.json": "antigravity"}
        for name, tool in wanted.items():
            with self.subTest(file=name):
                text = (ROOT / name).read_text()
                json.loads(text)
                self.assertIn(f"hook adapter {tool}", text)


if __name__ == "__main__":
    unittest.main()
