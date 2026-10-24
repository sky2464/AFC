"""Tests for the project lifecycle commands: pause, resume and remove."""

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


class PauseResumeTest(CliTestCase):
    def setUp(self):
        super().setUp()
        _, self.created = self.new()
        self.code = Path(self.created["code_path"])
        self.workspace = Path(self.created["workspace_path"])

    def test_pausing_the_active_project_parks_it(self):
        rc, out = run_cli(["pause", "kong-gateway-lab"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out, {"paused": "kong-gateway-lab", "was_active": True})
        reg = load_registry(self.home)
        self.assertEqual(reg.get("kong-gateway-lab").status, "paused")
        self.assertIsNone(reg.active_name)
        self.assertEqual(self.granted_in_settings(), [])
        self.assertTrue(self.code.is_dir() and self.workspace.is_dir())
        self.assertEqual(run_cli(["status"])[1],
                         {"active": None, "projects": [], "paused": ["kong-gateway-lab"]})

    def test_paused_projects_are_not_offered_for_picking(self):
        self.new("other-app")
        run_cli(["pause", "kong-gateway-lab"])
        run_cli(["pause", "other-app"])
        self.new("third-app")
        reg = load_registry(self.home)
        reg.active_name = None
        save_registry(self.home, reg)
        self.assertEqual(run_cli(["status"])[1], {
            "active": None, "projects": ["third-app"],
            "paused": ["kong-gateway-lab", "other-app"]})

    def test_pausing_another_project_keeps_the_active_one(self):
        self.new("other-app")
        rc, out = run_cli(["pause", "kong-gateway-lab"])
        self.assertEqual(rc, 0, out)
        self.assertFalse(out["was_active"])
        self.assertEqual(load_registry(self.home).active_name, "other-app")
        self.assertIn(str((self.parent / "other-app").resolve()), self.granted_in_settings())

    def test_resume_makes_it_active_again(self):
        run_cli(["pause", "kong-gateway-lab"])
        rc, out = run_cli(["resume", "kong-gateway-lab"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["resumed"], "kong-gateway-lab")
        reg = load_registry(self.home)
        self.assertEqual((reg.get("kong-gateway-lab").status, reg.active_name),
                         ("active", "kong-gateway-lab"))
        self.assertEqual(reg.get("kong-gateway-lab").last_active, date.today().isoformat())
        self.assertIn(str(self.code.resolve()), self.granted_in_settings())

    def test_switch_refuses_a_paused_project(self):
        self.new("other-app")
        run_cli(["pause", "kong-gateway-lab"])
        rc, out = run_cli(["switch", "kong-gateway-lab"])
        self.assertEqual(rc, 1)
        self.assertIn("is paused. Resume it", out["error"])
        self.assertEqual(load_registry(self.home).active_name, "other-app")

    def test_plain_errors(self):
        self.assertIn("isn't paused", run_cli(["resume", "kong-gateway-lab"])[1]["error"])
        run_cli(["pause", "kong-gateway-lab"])
        self.assertIn("already paused", run_cli(["pause", "kong-gateway-lab"])[1]["error"])
        self.assertIn("No project named nope", run_cli(["pause", "nope"])[1]["error"])
        self.assertIn("No project named nope", run_cli(["resume", "nope"])[1]["error"])

    def test_remove_works_on_a_paused_project(self):
        run_cli(["pause", "kong-gateway-lab"])
        rc, out = run_cli(["remove", "kong-gateway-lab"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(load_registry(self.home).projects, {})
