"""afc guard asks the same rules as the PreToolUse hook (FC-051 slice 2)."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from afc import cli
from afc.hooks import pretool

SAMPLES = [
    ("--shell", "git push --force", "Bash", {"command": "git push --force"}),
    ("--shell", "ls", "Bash", {"command": "ls"}),
    ("--write", "/etc/hosts", "Write", {"file_path": "/etc/hosts"}),
    ("--read", "/etc/hosts", "Read", {"file_path": "/etc/hosts"}),
]


class GuardCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-guard-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"AFC_HOME": str(self.tmp)})
        env.start()
        self.addCleanup(env.stop)
        for name in ("CLAUDE_CODE_SESSION_ID", "AFC_SESSION"):
            os.environ.pop(name, None)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return code, json.loads(out.getvalue())

    def test_same_answer_as_the_hook(self):
        for flag, value, tool, tool_input in SAMPLES:
            with self.subTest(flag=flag, value=value):
                code, result = self.run_cli("guard", flag, value, "--cwd", "/tmp")
                event = {"tool_name": tool, "tool_input": tool_input, "cwd": "/tmp"}
                reason = pretool.decide(event)
                self.assertEqual(result["allow"], reason is None)
                self.assertEqual(code, 0 if reason is None else 2)
                if reason:
                    self.assertEqual(result["reason"], reason)


if __name__ == "__main__":
    unittest.main()
