"""Tests for the health commands: check, repair and relocate."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

from afc.hooks.session_start import build_output
from afc.registry import load_registry
from afc.session_dirs import grant_dirs
from tests.helpers import run_cli
from tests.test_cli import CliTestCase


class HealthTest(CliTestCase):
    def setUp(self):
        super().setUp()
        _, self.created = self.new()
        self.code = Path(self.created["code_path"])
        self.workspace = Path(self.created["workspace_path"])

    def kinds(self) -> list[str]:
        rc, out = run_cli(["check"])
        self.assertEqual(rc, 0, out)
        return [p["kind"] for p in out["problems"]]

    def test_a_fresh_project_is_healthy(self):
        self.assertEqual(run_cli(["check"])[1], {"ok": True, "problems": []})

    def test_moved_code_folder_is_found_and_relocated(self):
        moved = self.tmp / "elsewhere"
        shutil.move(str(self.code), str(moved))
        rc, out = run_cli(["check"])
        missing = [p for p in out["problems"] if p["kind"] == "code_missing"]
        self.assertEqual(len(missing), 1)
        self.assertFalse(missing[0]["fixable"])
        self.assertIn("relocate it", missing[0]["detail"])
        rc, out = run_cli(["relocate", "kong-gateway-lab", "--path", str(moved)])
        self.assertEqual(rc, 0, out)
        self.assertEqual(load_registry(self.home).get("kong-gateway-lab").code_path, str(moved.resolve()))
        self.assertIn(str(moved.resolve()), self.granted_in_settings())
        self.assertEqual(self.kinds(), [])

    def test_relocate_refuses_bad_folders(self):
        self.assertIn("does not exist",
                      run_cli(["relocate", "kong-gateway-lab", "--path", str(self.tmp / "nope")])[1]["error"])
        self.assertIn("holds more than one project",
                      run_cli(["relocate", "kong-gateway-lab", "--path", str(self.home.parent)])[1]["error"])
        _, other = self.new("other-app")
        self.assertIn("already the code folder of other-app",
                      run_cli(["relocate", "kong-gateway-lab", "--path", other["code_path"]])[1]["error"])
        self.assertIn("No project named nope",
                      run_cli(["relocate", "nope", "--path", str(self.tmp)])[1]["error"])

    def test_missing_workspace_is_recreated(self):
        shutil.rmtree(self.workspace)
        self.assertIn("workspace_missing", self.kinds())
        rc, out = run_cli(["repair"])
        self.assertEqual(rc, 0, out)
        self.assertIn("Recreated the empty workspace for kong-gateway-lab.", out["repaired"])
        self.assertTrue((self.workspace / "plan" / "intent.md").is_file())
        self.assertEqual(out["left"], [])

    def test_leftover_workspace_is_put_away(self):
        ghost = self.home / "projects" / "ghost-app"
        (ghost / "plan").mkdir(parents=True)
        self.assertEqual(self.kinds(), ["orphan_workspace"])
        rc, out = run_cli(["repair"])
        self.assertEqual(rc, 0, out)
        self.assertFalse(ghost.exists())
        away = list((self.home / "removed").glob("ghost-app-*/workspace/plan"))
        self.assertEqual(len(away), 1)
        self.assertEqual(out["left"], [])

    def test_folder_access_is_set_back_to_the_active_project(self):
        other = self.tmp / "not-the-project"
        other.mkdir()
        grant_dirs(self.root, [other])
        path = self.root / ".claude" / "settings.local.json"
        settings = json.loads(path.read_text())
        mine, gone = str(self.tmp.resolve()), str(self.tmp / "gone-folder")
        settings["permissions"]["additionalDirectories"] += [mine, gone]
        path.write_text(json.dumps(settings))
        self.assertEqual(sorted(self.kinds()),
                         ["gone_access", "missing_access", "missing_access", "stale_access"])
        rc, out = run_cli(["repair"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["left"], [])
        granted = self.granted_in_settings()
        self.assertIn(str(self.code.resolve()), granted)
        self.assertIn(mine, granted)  # the user's own entry stays
        self.assertNotIn(str(other.resolve()), granted)
        self.assertNotIn(gone, granted)

    def test_a_missing_code_folder_is_left_for_the_user(self):
        shutil.rmtree(self.code)
        rc, out = run_cli(["repair"])
        self.assertEqual(rc, 0, out)
        self.assertEqual([p["kind"] for p in out["left"]], ["code_missing"])
        self.assertIn("kong-gateway-lab", load_registry(self.home).projects)

    def test_welcome_mentions_problems(self):
        ctx = lambda: build_output(self.home)["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("Health check", ctx())
        (self.home / "projects" / "ghost-app").mkdir()
        self.assertIn("Health check: 1 problem (sh bin/afc check).", ctx())
        with patch("afc.cli_health.find_problems", side_effect=RuntimeError("boom")):
            self.assertNotIn("Health check", ctx())
