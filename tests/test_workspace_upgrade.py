"""Tests for FC-011 slice 5: the workspace upgrades safely (numbered steps, backup, restore)."""

import sys
import tempfile
from datetime import date
from pathlib import Path
from unittest import mock

import afc

from afc import update_apply, workspace_upgrade as wu
from tests.helpers import AfcTestCase, RemoteCase, run_cli

DAY = date(2026, 10, 25)


class UpgradeTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        (self.home / "registry.json").write_text('{"projects": 1}')
        (self.home / "proj").mkdir()
        (self.home / "proj" / "plan.md").write_text("plan")
        self.log = []

    def step(self, number, fail=False):
        def run(home):
            self.log.append(number)
            (home / f"step{number}.txt").write_text("done")
            (home / "registry.json").write_text(f'{{"layout": {number}}}')
            if fail:
                raise RuntimeError("boom")
        return number, run

    def up(self, steps, old="v0.01a"):
        return wu.upgrade(self.home, old, steps=steps, today=DAY)

    def test_missing_layout_file_means_layout_zero(self):
        self.assertEqual(wu.recorded(self.home), 0)

    def test_steps_run_once_each_in_order(self):
        out = self.up([self.step(2), self.step(1), self.step(3)])
        self.assertEqual(self.log, [1, 2, 3])
        self.assertTrue(out["upgraded"])
        self.assertEqual(wu.recorded(self.home), 3)
        self.log.clear()
        again = self.up([self.step(1), self.step(2), self.step(3)])
        self.assertEqual(self.log, [])
        self.assertFalse(again["upgraded"])

    def test_only_missing_steps_run(self):
        (self.home / "layout").write_text("1\n")
        self.up([self.step(1), self.step(2)])
        self.assertEqual(self.log, [2])

    def test_nothing_to_do_makes_no_backup(self):
        out = self.up([])
        self.assertFalse(out["upgraded"])
        self.assertFalse((self.home / "backups").exists())

    def test_backup_is_made_before_steps_run(self):
        out = self.up([self.step(1)])
        saved = self.home / "backups" / "2026-10-25-v0.01a"
        self.assertEqual(out["backup"], str(saved))
        self.assertEqual((saved / "registry.json").read_text(), '{"projects": 1}')
        self.assertEqual((saved / "proj" / "plan.md").read_text(), "plan")
        self.assertFalse((saved / "step1.txt").exists())
        self.assertFalse((saved / "backups").exists())

    def test_second_backup_the_same_day_does_not_overwrite(self):
        self.up([self.step(1)])
        self.up([self.step(2)])
        self.assertEqual(len(list((self.home / "backups").iterdir())), 2)

    def test_failed_step_restores_the_backup_and_says_so(self):
        out = self.up([self.step(1), self.step(2, fail=True), self.step(3)])
        self.assertEqual(self.log, [1, 2])
        self.assertTrue(out["failed"] and out["restored"] and not out["upgraded"])
        self.assertEqual(out["step"], 2)
        self.assertIn("restored", out["summary"])
        self.assertEqual((self.home / "registry.json").read_text(), '{"projects": 1}')
        self.assertFalse((self.home / "step1.txt").exists())
        self.assertFalse((self.home / "layout").exists())
        self.assertEqual(wu.recorded(self.home), 0)
        self.assertEqual((self.home / "proj" / "plan.md").read_text(), "plan")
        self.assertTrue((self.home / "backups" / "2026-10-25-v0.01a").is_dir())

    def test_project_code_folders_outside_the_workspace_are_untouched(self):
        code = self.tmp / "app"
        code.mkdir()
        (code / "main.py").write_text("print(1)")
        self.up([self.step(1, fail=True)])
        self.assertEqual((code / "main.py").read_text(), "print(1)")

    def test_failed_backup_changes_nothing(self):
        with mock.patch("afc.workspace_upgrade.backup", side_effect=OSError("disk full")):
            out = self.up([self.step(1)])
        self.assertEqual(self.log, [])
        self.assertTrue(out["failed"])
        self.assertFalse(out["upgraded"])

    def test_steps_order_by_number_not_by_text(self):
        out = self.up([self.step(10), self.step(2), self.step(1)])
        self.assertEqual(self.log, [1, 2, 10])
        self.assertEqual(out["steps"], [1, 2, 10])
        self.assertEqual(wu.recorded(self.home), 10)

    def test_shipped_steps_are_found_imported_and_ordered_by_number(self):
        steps_dir = Path(tempfile.mkdtemp(dir=self.tmp))
        for n, body in ((2, "ok"), (10, "ok"), (11, "boom")):
            (steps_dir / f"upgrade_{n:03d}.py").write_text(
                "def run(home):\n"
                f"    (home / 'shipped{n}.txt').write_text('x')\n"
                + ("    raise RuntimeError('boom')\n" if body == "boom" else ""))
        (steps_dir / "upgrade_notes.py").write_text("raise SystemExit('not a step')\n")
        before = set(sys.modules)
        with mock.patch.object(afc, "__path__", list(afc.__path__) + [str(steps_dir)]):
            try:
                self.assertEqual([n for n, _ in wu.shipped_steps()], [2, 10, 11])
                out = wu.upgrade(self.home, "v0.01a", today=DAY)
            finally:
                for name in set(sys.modules) - before:
                    if name.startswith("afc.upgrade_"):
                        del sys.modules[name]
        self.assertTrue(out["failed"] and out["restored"])
        self.assertEqual(out["step"], 11)
        self.assertFalse((self.home / "shipped2.txt").exists())
        self.assertEqual(wu.recorded(self.home), 0)
        self.assertEqual((self.home / "registry.json").read_text(), '{"projects": 1}')

    def test_shipped_steps_have_unique_increasing_numbers(self):
        numbers = [n for n, _ in wu.shipped_steps()]
        self.assertEqual(numbers, sorted(set(numbers)))

    def test_cli_upgrade_without_flag_names_the_backup_after_the_installed_version(self):
        (self.home / "layout").write_text("0\n")
        with mock.patch("afc.workspace_upgrade.shipped_steps", return_value=[self.step(1)]):
            code, out = run_cli(["upgrade"])
        self.assertEqual(code, 0)
        names = [p.name for p in (self.home / "backups").iterdir()]
        self.assertEqual(len(names), 1)
        self.assertNotIn("unknown", names[0])
        self.assertRegex(names[0], r"^\d{4}-\d{2}-\d{2}-v\d")

    def test_cli_upgrade_runs_the_command(self):
        code, out = run_cli(["upgrade", "--from-version", "v0.01a"])
        self.assertEqual(code, 0)
        self.assertIn("upgraded", out)


class ApplyUpgradesTest(RemoteCase):
    def test_update_upgrades_the_workspace_after_the_code(self):
        self.commit("v0.02a")
        self.tag("v0.02a")
        report = {"upgraded": True, "summary": "Your workspace was upgraded; a backup is in X."}
        with mock.patch("afc.update_apply.run_check", return_value={"ok": True, "problems": []}), \
                mock.patch("afc.update_apply.run_upgrade", return_value=report) as up:
            out = update_apply.apply(self.copy, self.home)
        up.assert_called_once_with(self.copy, "v0.01a")
        self.assertEqual(out["workspace"], report)
        self.assertIn("workspace was upgraded", out["summary"])

    def test_unreadable_upgrade_is_not_silent(self):
        self.commit("v0.02a")
        self.tag("v0.02a")
        with mock.patch("afc.update_apply.run_check", return_value={"ok": True, "problems": []}), \
                mock.patch("afc.update_apply.run_upgrade", return_value=None):
            out = update_apply.apply(self.copy, self.home)
        self.assertTrue(out["updated"])
        self.assertIn("workspace upgrade could not be run", out["summary"])

    def test_refused_update_does_not_touch_the_workspace(self):
        (self.copy / "x.txt").write_text("edit")
        self.commit("v0.02a")
        self.tag("v0.02a")
        with mock.patch("afc.update_apply.run_upgrade") as up:
            update_apply.apply(self.copy, self.home)
        up.assert_not_called()
