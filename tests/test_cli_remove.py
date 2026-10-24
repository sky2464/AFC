"""Tests for the remove command."""

import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch

from afc.registry import load_registry, save_registry
from tests.helpers import run_cli
from tests.test_cli import CliTestCase


class RemoveTest(CliTestCase):
    def setUp(self):
        super().setUp()
        _, self.created = self.new()
        self.code = Path(self.created["code_path"])
        self.workspace = Path(self.created["workspace_path"])
        self.away = self.home.resolve() / "removed" / f"kong-gateway-lab-{date.today():%Y%m%d}"

    def test_removes_the_active_project_and_keeps_its_code(self):
        rc, out = run_cli(["remove", "kong-gateway-lab"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out, {
            "removed": "kong-gateway-lab", "was_active": True,
            "moved": {"workspace": str(self.away / "workspace")},
            "code_left_at": str(self.code)})
        self.assertFalse(self.workspace.exists())
        self.assertTrue((self.away / "workspace" / "plan").is_dir())
        self.assertTrue(self.code.is_dir())
        reg = load_registry(self.home)
        self.assertEqual((reg.projects, reg.active_name), ({}, None))
        self.assertEqual(self.granted_in_settings(), [])
        self.assertEqual(run_cli(["status"])[1], {"active": None, "projects": []})

    def test_code_moves_only_when_asked(self):
        rc, out = run_cli(["remove", "kong-gateway-lab", "--code"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["moved"]["code"], str(self.away / "code"))
        self.assertNotIn("code_left_at", out)
        self.assertFalse(self.code.exists())
        self.assertTrue((self.away / "code" / ".git").is_dir())

    def test_removing_another_project_keeps_the_active_one(self):
        self.new("other-app")
        rc, out = run_cli(["remove", "kong-gateway-lab"])
        self.assertEqual(rc, 0, out)
        self.assertFalse(out["was_active"])
        reg = load_registry(self.home)
        self.assertEqual((list(reg.projects), reg.active_name), (["other-app"], "other-app"))
        self.assertIn(str((self.parent / "other-app").resolve()), self.granted_in_settings())

    def test_same_name_removed_twice_gets_its_own_folder(self):
        run_cli(["remove", "kong-gateway-lab", "--code"])
        self.new()
        rc, out = run_cli(["remove", "kong-gateway-lab"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["moved"]["workspace"],
                         str(self.away.with_name(self.away.name + "-2") / "workspace"))

    def test_unknown_project(self):
        rc, out = run_cli(["remove", "nope"])
        self.assertEqual(rc, 1)
        self.assertIn("No project named nope", out["error"])

    def test_refuses_a_code_folder_that_holds_more(self):
        reg = load_registry(self.home)
        reg.update("kong-gateway-lab", code_path=str(self.home.parent))
        save_registry(self.home, reg)
        rc, out = run_cli(["remove", "kong-gateway-lab", "--code"])
        self.assertEqual(rc, 1)
        self.assertIn("holds more than this project", out["error"])
        self.assertTrue(self.workspace.is_dir())
        self.assertIn("kong-gateway-lab", load_registry(self.home).projects)

    def test_failure_puts_everything_back(self):
        real_move = shutil.move
        calls = []

        def flaky(src, dst):
            calls.append(src)
            if len(calls) == 2:
                raise OSError("disk full")
            return real_move(src, dst)

        before = self.granted_in_settings()
        with patch("afc.cli.shutil.move", side_effect=flaky):
            rc, out = run_cli(["remove", "kong-gateway-lab", "--code"])
        self.assertEqual(rc, 1)
        self.assertIn("disk full", out["error"])
        self.assertTrue(self.workspace.is_dir() and self.code.is_dir())
        self.assertFalse(self.away.exists())
        self.assertEqual(load_registry(self.home).active_name, "kong-gateway-lab")
        self.assertEqual(self.granted_in_settings(), before)
