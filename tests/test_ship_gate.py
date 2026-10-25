"""Tests for the FC-015 readiness gate: `sh bin/afc ship --check <id>`, one test per check."""

import subprocess
from pathlib import Path

from afc import ship
from tests.helpers import run_cli
from tests.test_cli import CliTestCase

PASS = "python3 -c 'import sys; sys.exit(0)'"
FAIL = "python3 -c 'import sys; sys.exit(1)'"


def _spec_hash(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ShipGateTest(CliTestCase):
    def setUp(self):
        super().setUp()
        rc, out = self.new()
        self.assertEqual(rc, 0)
        self.ws = Path(out["workspace_path"])
        self.code = Path(out["code_path"])
        run_cli(["plan", "add", "Thing"])
        run_cli(["plan", "start", "S-001"])
        self.spec = next((self.ws / "plan" / "specs").glob("S-001-*.md"))
        self.tick(True)
        self.record_tests(PASS)
        subprocess.run(["git", "add", "-A"], cwd=self.code)
        subprocess.run(["git", "-c", "user.name=a", "-c", "user.email=a@b.c", "commit", "-qm", "x"],
                       cwd=self.code)

    def tick(self, done):
        text = self.spec.read_text(encoding="utf-8")
        mark = "[x]" if done else "[ ]"
        for old in ("- [ ] 1.", "- [x] 1."):
            text = text.replace(old, f"- {mark} 1.")
        if "- [" not in text:
            text = text.replace("## Slices\n", f"## Slices\n\n- {mark} 1. Only — you'll check it by x\n", 1)
        self.spec.write_text(text, encoding="utf-8")

    def record_tests(self, command):
        arch = self.ws / "plan" / "architecture.md"
        text = arch.read_text(encoding="utf-8") if arch.is_file() else ""
        lines = [l for l in text.splitlines() if not l.startswith("Test command:")]
        arch.write_text("\n".join(lines + [f"Test command: {command}"]) + "\n", encoding="utf-8")

    def check(self):
        rc, out = run_cli(["ship", "--check", "S-001"])
        self.assertEqual(rc, 0, out)
        return out

    def test_clean_project_is_ready(self):
        out = self.check()
        self.assertTrue(out["ready"])
        self.assertEqual(out["missing"], [])

    def test_open_slice_is_missing(self):
        self.tick(False)
        out = self.check()
        self.assertFalse(out["ready"])
        self.assertEqual(len(out["missing"]), 1)
        self.assertIn("slice", out["missing"][0])
        self.assertIn("1.", out["missing"][0])

    def test_failing_suite_is_missing(self):
        self.record_tests(FAIL)
        out = self.check()
        self.assertEqual(len(out["missing"]), 1)
        self.assertIn("test", out["missing"][0].lower())

    def test_no_test_command_is_missing_never_passing(self):
        (self.ws / "plan" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
        out = self.check()
        self.assertFalse(out["ready"])
        self.assertIn("no test command", out["missing"][0].lower())

    def test_dirty_tree_is_missing(self):
        (self.code / "new.txt").write_text("hi\n", encoding="utf-8")
        out = self.check()
        self.assertEqual(len(out["missing"]), 1)
        self.assertIn("uncommitted", out["missing"][0])

    def test_all_three_listed_together_and_nothing_changes(self):
        self.tick(False)
        self.record_tests(FAIL)
        (self.code / "new.txt").write_text("hi\n", encoding="utf-8")
        before = (self.ws / "plan" / "master-plan.md").read_text(encoding="utf-8")
        spec_before = _spec_hash(self.spec)
        out = self.check()
        self.assertEqual(len(out["missing"]), 3)
        self.assertTrue(out["next"])
        self.assertEqual((self.ws / "plan" / "master-plan.md").read_text(encoding="utf-8"), before)
        self.assertEqual(_spec_hash(self.spec), spec_before)
        self.assertFalse((self.code / "changelog.md").exists())

    def test_spec_not_in_progress(self):
        rc, out = run_cli(["ship", "--check", "S-009"])
        self.assertNotEqual(rc, 0)

    def test_gate_function_without_test_command(self):
        self.assertIn("no test command", ship.tests_green(self.code, None)[0].lower())
