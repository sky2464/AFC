import shutil
from pathlib import Path

from tests.helpers import run_cli
from tests.test_cli import CliTestCase


class PlanCommandsTest(CliTestCase):
    def setUp(self):
        super().setUp()
        rc, out = self.new()
        self.assertEqual(rc, 0)
        self.ws = Path(out["workspace_path"])
        self.master = self.ws / "plan" / "master-plan.md"

    def spec_file(self, sid):
        return next((self.ws / "plan" / "specs").glob(f"{sid}-*.md"))

    def write_slices(self, sid, slices):
        path = self.spec_file(sid)
        text = path.read_text(encoding="utf-8")
        body = "\n".join(slices) + "\n"
        path.write_text(text.replace("## Slices\n", "## Slices\n\n" + body, 1), encoding="utf-8")

    def assertError(self, argv, message):
        rc, out = run_cli(argv)
        self.assertNotEqual(rc, 0)
        self.assertEqual(out["error"], message)

    def test_add_creates_specs_in_order(self):
        rc, a = run_cli(["plan", "add", "First thing"])
        self.assertEqual(rc, 0)
        self.assertEqual(a["created"], "S-001")
        self.assertEqual(a["size"], "M")
        self.assertEqual(a["title"], "First thing")
        rc, b = run_cli(["plan", "add", "Second thing", "--size", "L"])
        self.assertEqual(b["created"], "S-002")
        self.assertTrue(self.spec_file("S-001").is_file())
        self.assertTrue(self.spec_file("S-002").name.startswith("S-002-second-thing"))
        text = self.spec_file("S-002").read_text(encoding="utf-8")
        self.assertIn("# S-002 — Second thing", text)
        self.assertIn("Size: L", text)
        rc, p = run_cli(["plan"])
        self.assertEqual([r["id"] for r in p["next"]], ["S-001", "S-002"])
        self.assertIsNone(p["now"])
        self.assertEqual(p["done_count"], 0)

    def test_add_in_old_workspace_without_folders(self):
        shutil.rmtree(self.ws / "plan" / "specs", ignore_errors=True)
        shutil.rmtree(self.ws / "plan" / "archive", ignore_errors=True)
        rc, out = run_cli(["plan", "add", "Old"])
        self.assertEqual(rc, 0)
        self.assertTrue(self.spec_file("S-001").is_file())
        self.assertTrue((self.ws / "plan" / "archive").is_dir())

    def test_empty_title(self):
        self.assertError(["plan", "add", "  "], "Give the spec a title.")

    def test_full_flow(self):
        run_cli(["plan", "add", "First"])
        run_cli(["plan", "add", "Second"])
        self.write_slices("S-001", ["- [ ] one", "- [ ] two"])
        rc, out = run_cli(["plan", "start", "S-001"])
        self.assertEqual(rc, 0)
        self.assertEqual(out["started"], "S-001")
        self.assertEqual(out["next_slice"], "one")
        self.assertIn("Status: in progress", self.spec_file("S-001").read_text(encoding="utf-8"))
        rc, p = run_cli(["plan"])
        self.assertEqual(p["now"]["id"], "S-001")
        self.assertEqual(p["now"]["next_slice"], "one")
        self.assertEqual([r["id"] for r in p["next"]], ["S-002"])
        self.assertError(["plan", "start", "S-002"], "S-001 is still in progress. Finish it first.")
        self.assertError(["plan", "done", "S-001"], "S-001 still has 2 open slice(s), starting with: one")
        path = self.spec_file("S-001")
        path.write_text(path.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
        rc, out = run_cli(["plan", "done", "S-001"])
        self.assertEqual(rc, 0)
        self.assertEqual(out["done"], "S-001")
        self.assertEqual(out["suggest_next"]["id"], "S-002")
        archived = self.ws / "plan" / "archive" / out["archived"].split("/")[-1]
        self.assertTrue(archived.is_file())
        self.assertFalse(list((self.ws / "plan" / "specs").glob("S-001-*")))
        arch = archived.read_text(encoding="utf-8")
        self.assertIn("Status: done", arch)
        self.assertIn("Slices: 2.", arch)
        index = (self.ws / "plan" / "archive" / "index.md").read_text(encoding="utf-8")
        self.assertIn("# Archive", index)
        self.assertIn(f"| S-001 | First |", index)
        master = self.master.read_text(encoding="utf-8")
        self.assertIn("(archive/", master)
        self.assertIn("S-001 done", master)
        rc, p = run_cli(["plan"])
        self.assertIsNone(p["now"])
        self.assertEqual(p["done_count"], 1)

    def test_done_without_slices(self):
        run_cli(["plan", "add", "First"])
        run_cli(["plan", "start", "S-001"])
        self.assertError(["plan", "done", "S-001"], "S-001 has no slices yet.")

    def test_done_not_in_now_and_start_not_in_next(self):
        run_cli(["plan", "add", "First"])
        self.assertError(["plan", "done", "S-001"], "S-001 isn't in progress.")
        self.write_slices("S-001", ["- [x] a"])
        run_cli(["plan", "start", "S-001"])
        self.assertError(["plan", "start", "S-001"], "S-001 is still in progress. Finish it first.")
        run_cli(["plan", "done", "S-001"])
        self.assertError(["plan", "start", "S-001"], "S-001 isn't waiting in Next.")

    def test_unknown_id(self):
        self.assertError(["plan", "start", "S-009"], "No spec S-009 in the master plan.")
        self.assertError(["plan", "done", "S-009"], "No spec S-009 in the master plan.")

    def test_missing_spec_file_leaves_plan_unchanged(self):
        run_cli(["plan", "add", "First"])
        self.spec_file("S-001").unlink()
        before = self.master.read_text(encoding="utf-8")
        rc, out = run_cli(["plan", "start", "S-001"])
        self.assertNotEqual(rc, 0)
        self.assertTrue(out["error"].startswith("The spec file for S-001 is missing: "))
        self.assertEqual(self.master.read_text(encoding="utf-8"), before)

    def test_no_master_plan(self):
        self.master.unlink()
        msg = "This project has no master plan yet. A health check repair adds one."
        for argv in (["plan"], ["plan", "add", "x"], ["plan", "start", "S-001"], ["plan", "done", "S-001"]):
            self.assertError(argv, msg)

    def test_goal(self):
        text = self.master.read_text(encoding="utf-8")
        self.master.write_text(text.replace("## Goal\n", "## Goal\n\nShip the thing.\n", 1), encoding="utf-8")
        rc, p = run_cli(["plan"])
        self.assertEqual(p["goal"], "Ship the thing.")
