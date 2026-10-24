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

    def test_old_progress_list_is_upgraded(self):
        plan_dir = self.workspace / "plan"
        (plan_dir / "master-plan.md").unlink()
        shutil.rmtree(plan_dir / "specs", ignore_errors=True)
        shutil.rmtree(plan_dir / "archive", ignore_errors=True)
        (plan_dir / "progress.md").write_text("# Progress\n\n## Now\n\nold slice\n", encoding="utf-8")
        rc, out = run_cli(["check"])
        found = [p for p in out["problems"] if p["kind"] == "old_plan_format"]
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["fixable"])
        self.assertEqual(found[0]["path"], str(plan_dir))
        rc, out = run_cli(["repair"])
        self.assertEqual(rc, 0, out)
        self.assertIn("Upgraded kong-gateway-lab to a master plan.", out["repaired"])
        self.assertEqual(out["left"], [])
        master = (plan_dir / "master-plan.md").read_text(encoding="utf-8")
        self.assertIn("## Earlier progress", master)
        self.assertIn("old slice", master.split("## Earlier progress")[1])
        self.assertNotIn("# Progress", master.split("## Earlier progress")[1])
        self.assertTrue((plan_dir / "archive" / "progress-legacy.md").is_file())
        self.assertFalse((plan_dir / "progress.md").exists())
        self.assertTrue((plan_dir / "specs").is_dir())
        self.assertEqual(run_cli(["plan"])[0], 0)

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

    # -- account add-ons that don't belong

    def addons_reported(self, enabled=("agent-recall@synced",)):
        plugins = [{"id": "superpowers@claude-plugins-official", "enabled": True},
                   *({"id": i, "enabled": True} for i in enabled)]
        return patch("afc.addons.reported", return_value=(plugins, None))

    def local_settings(self):
        return json.loads((self.root / ".claude" / "settings.local.json").read_text())

    def allow_list(self, *ids):
        (self.root / "afc-addons.json").write_text(json.dumps({"allowed": list(ids)}))

    def test_an_add_on_not_on_the_list_is_found_then_switched_off(self):
        self.allow_list("superpowers@claude-plugins-official")
        with self.addons_reported():
            rc, out = run_cli(["check"])
            found = [p for p in out["problems"] if p["kind"] == "addon_not_allowed"]
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0]["fixable"])
            self.assertIn("agent-recall@synced", found[0]["detail"])
            self.assertIn("still works everywhere else", found[0]["detail"])
            rc, out = run_cli(["repair"])
        self.assertEqual(rc, 0, out)
        self.assertIn("Switched off 1 add-on in Flight Control sessions; this applies from the next start.",
                      out["repaired"])
        settings = self.local_settings()
        self.assertEqual(settings["enabledPlugins"], {"agent-recall@synced": False})
        self.assertEqual(settings["afcBlockedAddons"], ["agent-recall@synced"])

    def test_the_users_own_entries_and_other_keys_stay(self):
        self.allow_list("superpowers@claude-plugins-official")
        path = self.root / ".claude" / "settings.local.json"
        path.write_text(json.dumps({"enabledPlugins": {"mine@x": False, "keep@x": True}, "other": 1}))
        with self.addons_reported():
            run_cli(["repair"])
        settings = self.local_settings()
        self.assertEqual(settings["enabledPlugins"],
                         {"mine@x": False, "keep@x": True, "agent-recall@synced": False})
        self.assertEqual(settings["other"], 1)

    def test_allowing_an_add_on_again_removes_the_block(self):
        self.allow_list("superpowers@claude-plugins-official")
        path = self.root / ".claude" / "settings.local.json"
        path.write_text(json.dumps({"enabledPlugins": {"mine@x": False}}))
        with self.addons_reported():
            run_cli(["repair"])
        self.allow_list("superpowers@claude-plugins-official", "agent-recall@synced")
        with self.addons_reported(enabled=()):
            self.assertIn("addon_unblock", self.kinds())
            rc, out = run_cli(["repair"])
            self.assertEqual(out["left"], [])
        settings = self.local_settings()
        self.assertEqual(settings["enabledPlugins"], {"mine@x": False})
        self.assertEqual(settings["afcBlockedAddons"], [])

    def test_unknown_add_on_state_is_not_a_problem(self):
        with patch("afc.addons.reported", return_value=([], "no claude")):
            self.assertEqual(self.kinds(), [])


    def test_welcome_mentions_problems(self):
        ctx = lambda: build_output(self.home)["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("Health check", ctx())
        (self.home / "projects" / "ghost-app").mkdir()
        self.assertIn("Health check: 1 problem (sh bin/afc check).", ctx())
        with patch("afc.cli_health.find_problems", side_effect=RuntimeError("boom")):
            self.assertNotIn("Health check", ctx())
