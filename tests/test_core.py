"""The five core tests (FC-030): the things that can hurt a user if they break silently.

Each test builds its own AFC_HOME and folders; nothing is shared.
"""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from afc.config import afc_root
from afc.hooks.common import Context
from afc.hooks.rules_git import check_git
from afc.hooks.rules_paths import check_paths
from afc.hooks.rules_secrets import check_secrets
from afc.hooks.session_start import BANNER, build_output
from afc.registry import Project, Registry, load_registry, save_registry


def event(tool, tool_input, cwd="/"):
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": str(cwd)}


class CoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-core-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.app = self.tmp / "app"
        self.ws = self.home / "projects" / "demo"
        for d in (self.home, self.app):
            d.mkdir()
        self.ws.mkdir(parents=True)
        self.project = Project(name="demo", code_path=str(self.app), workspace_path=str(self.ws))
        self.ctx = Context(home=self.home, root=afc_root(), active=self.project, maintain=False)


class CoreTests(CoreCase):
    def test_path_guard_keeps_code_inside_the_project(self):
        inside = event("Write", {"file_path": str(self.app / "a.py"), "content": "x = 1"}, self.app)
        self.assertIsNone(check_paths(inside, self.ctx))
        elsewhere = Path.home() / "afc-core-elsewhere.py"
        outside = event("Write", {"file_path": str(elsewhere), "content": "x = 1"}, self.app)
        self.assertIsNotNone(check_paths(outside, self.ctx))
        shell = event("Bash", {"command": f"echo x > {elsewhere}"}, self.app)
        self.assertIsNotNone(check_paths(shell, self.ctx))

    def test_secret_check_blocks_a_key(self):
        key = "AKIA" + "ABCDEFGHIJKLMNOP"
        bad = event("Write", {"file_path": str(self.app / "c.py"), "content": f'KEY = "{key}"'}, self.app)
        reason = check_secrets(bad, self.ctx)
        self.assertIsNotNone(reason)
        self.assertNotIn(key, reason)
        good = event("Write", {"file_path": str(self.app / "c.py"), "content": "KEY = os.environ['KEY']"}, self.app)
        self.assertIsNone(check_secrets(good, self.ctx))

    def test_risky_git_is_blocked(self):
        for cmd in ("git push --force origin main", "git push -f", "git branch -D old", "git reset --hard HEAD~1"):
            self.assertIsNotNone(check_git(event("Bash", {"command": cmd}, self.app), self.ctx), cmd)
        for cmd in ("git status", "git push origin main"):
            self.assertIsNone(check_git(event("Bash", {"command": cmd}, self.app), self.ctx), cmd)

    def test_remove_moves_and_deletes_nothing(self):
        from afc import cli

        (self.ws / "plan").mkdir()
        (self.ws / "plan" / "p.md").write_text("plan")
        (self.app / "main.py").write_text("code")
        reg = Registry()
        reg.add(self.project)
        reg.set_active("demo")
        save_registry(self.home, reg)
        root = self.tmp / "root"
        root.mkdir()
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"AFC_HOME": str(self.home)}), \
                mock.patch("afc.cli.afc_root", return_value=root), \
                contextlib.redirect_stdout(buf):
            code = cli.main(["remove", "demo"])
        out = json.loads(buf.getvalue())
        self.assertEqual(code, 0, out)
        moved = Path(out["moved"]["workspace"])
        self.assertTrue(str(moved).startswith(str(self.home / "removed")))
        self.assertEqual((moved / "plan" / "p.md").read_text(), "plan")
        self.assertFalse(self.ws.exists())
        self.assertEqual((self.app / "main.py").read_text(), "code")
        self.assertEqual(load_registry(self.home).projects, {})

    def test_welcome_survives_a_broken_registry(self):
        (self.home / "projects.json").write_text("{")
        out = build_output(self.home)
        self.assertEqual(out["systemMessage"], BANNER)
        self.assertIn("Registry unreadable", out["hookSpecificOutput"]["additionalContext"])
        with mock.patch("afc.hooks.session_start.load_registry", side_effect=RuntimeError("boom")):
            self.assertEqual(build_output(self.home)["systemMessage"], BANNER)


if __name__ == "__main__":
    unittest.main()
