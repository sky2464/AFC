import json
import shutil
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from afc.config import afc_root
from afc.registry import load_registry, save_registry
from tests.helpers import AfcTestCase, run_cli

REAL_TEMPLATES = afc_root() / "templates"


class CliTestCase(AfcTestCase):
    """Isolated AFC_HOME plus a scratch A-FC root for settings writes.

    afc.cli.afc_root is patched to a scratch root that holds a copy of the real
    templates/, so grant_dirs writes there and app templates still come from the
    repo. afc.workspace keeps the real root and reads the real plan templates.
    """

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "root"
        shutil.copytree(REAL_TEMPLATES, self.root / "templates")
        patcher = patch("afc.cli.afc_root", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        # never ask the real Claude Code about the owner's add-ons
        quiet = patch("afc.addons.reported", return_value=([], None))
        quiet.start()
        self.addCleanup(quiet.stop)
        self.parent = self.tmp / "work"
        self.parent.mkdir()

    def new(self, name="kong-gateway-lab", *extra):
        return run_cli(
            [
                "new",
                "--name",
                name,
                "--parent",
                str(self.parent),
                "--git-name",
                "Sky",
                "--git-email",
                "s@example.com",
                *extra,
            ]
        )

    def granted_in_settings(self) -> list[str]:
        path = self.root / ".claude" / "settings.local.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["permissions"]["additionalDirectories"]


class NewTest(CliTestCase):
    def test_new_creates_everything(self):
        rc, out = self.new()
        self.assertEqual(rc, 0)
        code = Path(out["code_path"])
        self.assertTrue((code / ".git").is_dir() and (code / "README.md").exists())
        self.assertFalse((code / "graph").exists())  # nothing of ours leaks into the app repo
        self.assertEqual(load_registry(self.home).active().name, "kong-gateway-lab")
        self.assertIn(str(code), out["granted"])
        self.assertEqual(out["project"], "kong-gateway-lab")
        self.assertTrue((Path(out["workspace_path"]) / "plan" / "intent.md").exists())
        self.assertFalse(out["icloud_synced"])

    def test_new_writes_app_templates_and_main_branch(self):
        rc, out = self.new()
        self.assertEqual(rc, 0)
        code = Path(out["code_path"])
        self.assertTrue((code / "README.md").read_text(encoding="utf-8").startswith("# kong-gateway-lab\n"))
        ignore = (code / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env.*", ignore)
        self.assertIn("!.env.example", ignore)
        branch = subprocess.run(
            ["git", "-C", str(code), "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(branch, "main")

    def test_new_sets_last_active_and_profile(self):
        rc, out = self.new("kong-gateway-lab", "--profile", "mvp", "--ai-trailer")
        self.assertEqual(rc, 0)
        project = load_registry(self.home).get("kong-gateway-lab")
        self.assertEqual(project.profile, "mvp")
        self.assertTrue(project.ai_trailer)
        self.assertEqual(project.last_active, date.today().isoformat())

    def test_new_grants_code_path_in_settings(self):
        rc, out = self.new()
        self.assertEqual(rc, 0)
        self.assertIn(out["code_path"], self.granted_in_settings())

    def test_new_refuses_non_empty_folder(self):
        target = self.parent / "kong-gateway-lab"
        target.mkdir()
        (target / "notes.txt").write_text("mine", encoding="utf-8")
        rc, out = self.new()
        self.assertEqual(rc, 1)
        self.assertIn("error", out)
        self.assertIsNone(load_registry(self.home).active())

    def test_new_rejects_bad_name(self):
        rc, out = self.new("../x")
        self.assertEqual(rc, 1)
        self.assertIn("error", out)
        self.assertEqual(list(self.parent.iterdir()), [])
        self.assertIsNone(load_registry(self.home).active())

    def test_new_rejects_unknown_profile(self):
        rc, out = self.new("kong-gateway-lab", "--profile", "banana")
        self.assertEqual(rc, 1)
        self.assertIn("error", out)

    def test_new_rejects_missing_parent(self):
        rc, out = run_cli(
            [
                "new",
                "--name",
                "kong-gateway-lab",
                "--parent",
                str(self.tmp / "nope"),
                "--git-name",
                "Sky",
                "--git-email",
                "s@example.com",
            ]
        )
        self.assertEqual(rc, 1)
        self.assertIn("error", out)

    def test_missing_option_gives_json_error(self):
        rc, out = run_cli(["new", "--name", "kong-gateway-lab"])
        self.assertEqual(rc, 1)
        self.assertIn("error", out)

    def test_enterprise_profile_warns_on_icloud(self):
        self.new()
        with patch("afc.cli.icloud_synced", return_value=True):
            rc, out = run_cli(["set", "profile", "enterprise"])
        self.assertEqual(rc, 0)
        self.assertIn("warning", out)

    def test_personal_profile_does_not_warn_on_icloud(self):
        self.new()
        with patch("afc.cli.icloud_synced", return_value=True):
            rc, out = run_cli(["set", "profile", "personal"])
        self.assertEqual(rc, 0)
        self.assertNotIn("warning", out)

    def test_new_in_icloud_folder_with_work_profile_warns(self):
        with patch("afc.cli.icloud_synced", return_value=True):
            rc, out = self.new("kong-gateway-lab", "--profile", "work")
        self.assertEqual(rc, 0)
        self.assertTrue(out["icloud_synced"])
        self.assertIn("warning", out)


class AdoptTest(CliTestCase):
    def test_adopt_registers_existing_folder(self):
        git_app = self.tmp / "git-app"
        (git_app / ".git").mkdir(parents=True)
        plain = self.tmp / "plain-app"
        plain.mkdir()

        rc, out = run_cli(["adopt", "--name", "git-app", "--path", str(git_app), "--git-name", "Sky", "--git-email", "s@example.com"])
        self.assertEqual(rc, 0)
        self.assertTrue(out["is_git"])
        self.assertEqual(load_registry(self.home).active().name, "git-app")
        self.assertIn(str(git_app.resolve()), out["granted"])

        rc, out = run_cli(["adopt", "--name", "plain-app", "--path", str(plain)])
        self.assertEqual(rc, 0)
        self.assertFalse(out["is_git"])
        self.assertEqual(load_registry(self.home).active().name, "plain-app")

    def test_adopt_missing_folder_errors(self):
        rc, out = run_cli(["adopt", "--name", "ghost", "--path", str(self.tmp / "nope")])
        self.assertEqual(rc, 1)
        self.assertIn("error", out)
        self.assertIsNone(load_registry(self.home).get("ghost"))


class SwitchTest(CliTestCase):
    def test_switch_unknown_project_points_to_afc(self):
        rc, out = run_cli(["switch", "nothing-here"])
        self.assertEqual(rc, 1)
        self.assertIn("/afc", out["error"])

    def test_switch_changes_active_and_grants_code_path(self):
        _, first = self.new("kong-gateway-lab")
        _, second = self.new("other-app")
        rc, out = run_cli(["switch", "kong-gateway-lab"])
        self.assertEqual(rc, 0)
        self.assertEqual(out["project"], "kong-gateway-lab")
        registry = load_registry(self.home)
        self.assertEqual(registry.active().name, "kong-gateway-lab")
        self.assertEqual(registry.get("kong-gateway-lab").last_active, date.today().isoformat())
        self.assertIn(first["code_path"], self.granted_in_settings())
        self.assertIn(str(Path(first["workspace_path"]).resolve()), self.granted_in_settings())
        self.assertNotIn(second["code_path"], self.granted_in_settings())  # only the active one


class ReadOnlyCommandsTest(CliTestCase):
    def test_list_shows_projects_and_active(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["list"])
        self.assertEqual(rc, 0)
        self.assertEqual(out["active"], "kong-gateway-lab")
        self.assertEqual([p["name"] for p in out["projects"]], ["kong-gateway-lab"])

    def test_status_reads_now_section(self):
        _, created = self.new("kong-gateway-lab")
        progress = Path(created["workspace_path"]) / "plan" / "progress.md"
        progress.write_text(
            "# Progress\n\n## Now\n\nWriting the health endpoint.\n\n## Done\n\n- slice 1\n",
            encoding="utf-8",
        )
        rc, out = run_cli(["status"])
        self.assertEqual(rc, 0)
        self.assertEqual(out["name"], "kong-gateway-lab")
        self.assertEqual(out["now"], "Writing the health endpoint.")

    def test_status_names_the_active_spec(self):
        self.new("kong-gateway-lab")
        run_cli(["plan", "add", "First thing"])
        run_cli(["plan", "start", "S-001"])
        rc, out = run_cli(["status"])
        self.assertEqual(rc, 0)
        self.assertTrue(out["now"].startswith("S-001 "), out["now"])

    def test_status_without_now_section_is_empty(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["status"])
        self.assertEqual(rc, 0)
        self.assertEqual(out["now"], "")

    def test_status_with_projects_but_none_active_lists_them(self):
        self.new("kong-gateway-lab")
        reg = load_registry(self.home)
        reg.active_name = None
        save_registry(self.home, reg)
        rc, out = run_cli(["status"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, {"active": None, "projects": ["kong-gateway-lab"]})

    def test_status_on_first_run_is_empty(self):
        rc, out = run_cli(["status"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, {"active": None, "projects": []})

    def test_open_prints_path_off_macos(self):
        _, created = self.new("kong-gateway-lab")
        with patch.object(sys, "platform", "linux"), patch("afc.cli.subprocess.run") as run:
            rc, out = run_cli(["open"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, {"opened": False, "path": created["workspace_path"]})
        run.assert_not_called()

    def test_open_runs_open_on_macos(self):
        _, created = self.new("kong-gateway-lab")
        with patch.object(sys, "platform", "darwin"), patch("afc.cli.subprocess.run") as run:
            rc, out = run_cli(["open"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, {"opened": True, "path": created["workspace_path"]})
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["open", created["workspace_path"]])


class ModulesTest(CliTestCase):
    def test_modules_uses_active_profile(self):
        self.new("kong-gateway-lab")
        run_cli(["set", "profile", "personal"])
        rc, out = run_cli(["modules", "--touches", "auth"])
        self.assertEqual(rc, 0)
        self.assertEqual(out["profile"], "personal")
        self.assertEqual(out["modules"], ["secrets", "identity", "input", "ai-safety"])

    def test_modules_without_active_project_asks_for_interview(self):
        rc, out = run_cli(["modules", "--touches", "auth"])
        self.assertEqual(rc, 1)
        self.assertIn("interview", out["error"])

    def test_modules_with_unknown_profile_asks_for_interview(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["modules", "--touches", "auth"])
        self.assertEqual(rc, 1)
        self.assertIn("interview", out["error"])


class SetTest(CliTestCase):
    def test_set_persists_free_text_field(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["set", "last_slice", "slice 3"])
        self.assertEqual(rc, 0)
        self.assertEqual(out["value"], "slice 3")
        self.assertEqual(load_registry(self.home).active().last_slice, "slice 3")

    def test_set_validates_team_mode(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["set", "team_mode", "banana"])
        self.assertEqual(rc, 1)
        self.assertIn("error", out)

    def test_set_validates_remote(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["set", "remote", "ftp"])
        self.assertEqual(rc, 1)
        self.assertEqual(load_registry(self.home).active().remote, "none")

    def test_set_profile_rejects_unknown_value(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["set", "profile", "unknown"])
        self.assertEqual(rc, 1)

    def test_set_ai_trailer_takes_true_or_false(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["set", "ai_trailer", "true"])
        self.assertEqual((rc, out["value"]), (0, True))
        self.assertTrue(load_registry(self.home).active().ai_trailer)
        rc, out = run_cli(["set", "ai_trailer", "maybe"])
        self.assertEqual(rc, 1)

    def test_set_unknown_field_errors(self):
        self.new("kong-gateway-lab")
        rc, out = run_cli(["set", "name", "other"])
        self.assertEqual(rc, 1)
        self.assertIn("error", out)

    def test_set_without_active_project_errors(self):
        rc, out = run_cli(["set", "last_slice", "x"])
        self.assertEqual(rc, 1)
        self.assertIn("/afc", out["error"])


class IcloudTest(CliTestCase):
    def test_icloud_synced_detection(self):
        from afc.cli import icloud_synced

        home = self.tmp / "home"
        mobile = home / "Library" / "Mobile Documents"
        with patch("afc.cli.Path.home", return_value=home):
            (home / "Documents" / "app").mkdir(parents=True)
            (home / "Projects" / "app").mkdir(parents=True)
            self.assertFalse(icloud_synced(home / "Documents" / "app"))
            (mobile / "com~apple~CloudDocs" / "Documents").mkdir(parents=True)
            self.assertTrue(icloud_synced(home / "Documents" / "app"))
            self.assertTrue(icloud_synced(home / "Desktop"))
            self.assertFalse(icloud_synced(home / "Projects" / "app"))
            self.assertTrue(icloud_synced(mobile / "anything"))


class PlainUsageErrorTest(CliTestCase):
    JARGON = ("argument", "invalid choice", "usage:")

    def assertPlain(self, out: dict) -> None:
        self.assertIn("error", out)
        for word in self.JARGON:
            self.assertNotIn(word, out["error"])

    def test_invalid_choice_is_plain(self):
        rc, out = run_cli(["maintain", "toggle"])
        self.assertEqual(rc, 1)
        self.assertPlain(out)
        self.assertEqual(out["error"], "Use one of: on, off, status.")

    def test_missing_required_flag_is_plain(self):
        rc, out = run_cli(["new", "--name", "kong-gateway-lab"])
        self.assertEqual(rc, 1)
        self.assertPlain(out)
        self.assertEqual(out["error"], "Missing --parent, --git-name and --git-email.")

    def test_unknown_command_is_plain(self):
        rc, out = run_cli(["bogus"])
        self.assertEqual(rc, 1)
        self.assertPlain(out)
        self.assertTrue(out["error"].startswith("Unknown command bogus."))

    def test_missing_command_is_plain(self):
        rc, out = run_cli([])
        self.assertEqual(rc, 1)
        self.assertPlain(out)


class NewRollbackTest(CliTestCase):
    def setUp(self):
        super().setUp()
        self.settings = self.root / ".claude" / "settings.local.json"
        self.target = self.parent / "kong-gateway-lab"
        self.workspace = self.home / "projects" / "kong-gateway-lab"

    def test_corrupt_settings_fail_before_creating_anything_then_retry_succeeds(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text("{not json", encoding="utf-8")

        rc, out = self.new()
        self.assertEqual(rc, 1)
        self.assertIn("error", out)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.workspace.exists())
        self.assertIsNone(load_registry(self.home).active())
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{not json")

        self.settings.write_text("{}", encoding="utf-8")
        rc, out = self.new()
        self.assertEqual(rc, 0)
        self.assertTrue((self.target / ".git").is_dir())
        self.assertTrue(self.workspace.is_dir())
        self.assertEqual(load_registry(self.home).active().name, "kong-gateway-lab")

    def test_failed_registry_save_rolls_back_and_retry_succeeds(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text(json.dumps({"model": "x"}), encoding="utf-8")
        before = self.settings.read_text(encoding="utf-8")

        with patch("afc.cli.save_registry", side_effect=OSError("disk full")):
            rc, out = self.new()
        self.assertEqual(rc, 1)
        self.assertIn("disk full", out["error"])
        self.assertFalse(self.target.exists())
        self.assertFalse(self.workspace.exists())
        self.assertEqual(self.settings.read_text(encoding="utf-8"), before)

        rc, out = self.new()
        self.assertEqual(rc, 0)
        self.assertEqual(load_registry(self.home).active().name, "kong-gateway-lab")

    def test_rollback_keeps_an_empty_folder_the_user_made(self):
        self.target.mkdir()
        with patch("afc.cli.save_registry", side_effect=OSError("disk full")):
            rc, out = self.new()
        self.assertEqual(rc, 1)
        self.assertTrue(self.target.is_dir())
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertFalse(self.workspace.exists())

        rc, out = self.new()
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
