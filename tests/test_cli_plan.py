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
        text = path.read_text(encoding="utf-8").replace("- [ ] 1. <label> — you'll check it by <how>\n", "")
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

    def test_goal_is_set_shown_by_plan_and_logged(self):
        rc, out = run_cli(["plan", "goal", "  A calm\nco-pilot for small  slices. "])
        self.assertEqual((rc, out), (0, {"goal": "A calm co-pilot for small slices."}))
        rc, p = run_cli(["plan"])
        self.assertEqual(p["goal"], "A calm co-pilot for small slices.")
        self.assertIn("Goal set", self.master.read_text(encoding="utf-8"))
        run_cli(["plan", "goal", "Second goal."])
        self.assertEqual(run_cli(["plan"])[1]["goal"], "Second goal.")

    def test_rename_changes_file_row_heading_and_log_together(self):
        run_cli(["plan", "add", "Old name"])
        rc, out = run_cli(["plan", "rename", "S-001", "Show the PHP version a site announces inside headers"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["renamed"], "S-001")
        specs = sorted(p.name for p in (self.ws / "plan" / "specs").glob("S-001-*"))
        self.assertEqual(specs, ["S-001-show-the-php-version-a-site-announces.md"])
        body = (self.ws / "plan" / "specs" / specs[0]).read_text(encoding="utf-8")
        self.assertTrue(body.startswith("# S-001 — Show the PHP version a site announces inside headers\n"))
        master = self.master.read_text(encoding="utf-8")
        self.assertIn("| S-001 | Show the PHP version a site announces inside headers | M | [spec](specs/S-001-show-the-php-version-a-site-announces.md) |", master)
        self.assertNotIn("old-name", master)
        self.assertIn("S-001 renamed", master)

    def test_rename_works_on_the_spec_in_progress_and_keeps_its_start_date(self):
        run_cli(["plan", "add", "First"])
        run_cli(["plan", "start", "S-001"])
        before = run_cli(["plan"])[1]["now"]
        rc, out = run_cli(["plan", "rename", "S-001", "Better name"])
        self.assertEqual(rc, 0, out)
        after = run_cli(["plan"])[1]["now"]
        self.assertEqual((after["id"], after["title"]), ("S-001", "Better name"))
        self.assertIn("S-001-better-name.md", after["spec"])
        self.assertIn(before["id"], self.master.read_text(encoding="utf-8"))

    def test_rename_refuses_unknown_finished_and_empty(self):
        self.assertError(["plan", "rename", "S-009", "x"], "No spec S-009 in the master plan.")
        run_cli(["plan", "add", "First"])
        self.assertError(["plan", "rename", "S-001", "   "], "Give the spec a title.")
        self.write_slices("S-001", ["- [x] one"])
        run_cli(["plan", "start", "S-001"])
        run_cli(["plan", "done", "S-001"])
        self.assertError(["plan", "rename", "S-001", "Again"], "S-001 is finished, so it can't be renamed.")

    def next_ids(self):
        from afc import plan as plan_module
        return [r[0] for r in plan_module.read_rows(self.master.read_text(encoding="utf-8"), "Next")]

    def test_drop_archives_the_spec_marked_dropped_and_never_deletes_it(self):
        for title in ("One", "Two"):
            run_cli(["plan", "add", title])
        rc, out = run_cli(["plan", "drop", "S-002"])
        self.assertEqual((rc, out["dropped"]), (0, "S-002"), out)
        self.assertEqual(self.next_ids(), ["S-001"])
        archived = self.ws / "plan" / "archive" / "S-002-two.md"
        self.assertIn("Status: dropped", archived.read_text(encoding="utf-8"))
        self.assertFalse(list((self.ws / "plan" / "specs").glob("S-002-*")))
        master = self.master.read_text(encoding="utf-8")
        self.assertIn("| S-002 | Two (dropped) |", master)
        self.assertIn("(archive/S-002-two.md)", master)
        self.assertIn("S-002 dropped", master)
        index = (self.ws / "plan" / "archive" / "index.md").read_text(encoding="utf-8")
        self.assertIn("| S-002 | Two (dropped) |", index)

    def test_drop_and_move_refuse_the_spec_in_progress_finished_and_unknown_ones(self):
        run_cli(["plan", "add", "One"])
        run_cli(["plan", "add", "Two"])
        run_cli(["plan", "start", "S-001"])
        self.assertError(["plan", "drop", "S-001"], "S-001 is in progress, so it can't be dropped. Finish it or rename it.")
        self.assertError(["plan", "move", "S-001", "--to", "1"], "S-001 is in progress, so it can't be moved.")
        self.assertError(["plan", "drop", "S-009"], "No spec S-009 in the master plan.")
        run_cli(["plan", "drop", "S-002"])
        self.assertError(["plan", "drop", "S-002"], "S-002 is finished, so it can't be dropped.")
        self.assertError(["plan", "move", "S-002", "--to", "1"], "S-002 is finished, so it can't be moved.")

    def test_move_changes_the_order_of_next(self):
        for title in ("One", "Two", "Three"):
            run_cli(["plan", "add", title])
        rc, out = run_cli(["plan", "move", "S-003", "--to", "1"])
        self.assertEqual((rc, out["moved"], out["position"]), (0, "S-003", 1), out)
        self.assertEqual(self.next_ids(), ["S-003", "S-001", "S-002"])
        run_cli(["plan", "move", "S-003", "--to", "3"])
        self.assertEqual(self.next_ids(), ["S-001", "S-002", "S-003"])
        self.assertIn("S-003 moved to position 3", self.master.read_text(encoding="utf-8"))

    def test_move_refuses_a_position_outside_next(self):
        run_cli(["plan", "add", "One"])
        run_cli(["plan", "add", "Two"])
        self.assertError(["plan", "move", "S-001", "--to", "3"], "Pick a position from 1 to 2.")
        self.assertError(["plan", "move", "S-001", "--to", "0"], "Pick a position from 1 to 2.")

    def test_goal_cannot_be_empty(self):
        self.assertError(["plan", "goal", "   "], "Give the goal as one line of text.")

    def test_plan_says_when_slices_are_unreadable(self):
        run_cli(["plan", "add", "First"])
        path = self.spec_file("S-001")
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("- [ ] 1. <label> — you'll check it by <how>", "- one\n- two"), encoding="utf-8")
        rc, out = run_cli(["plan", "start", "S-001"])
        self.assertEqual((out["next_slice"], out["slices"]), (None, "unreadable"))
        rc, p = run_cli(["plan"])
        self.assertEqual((p["now"]["next_slice"], p["now"]["slices"]), (None, "unreadable"))

    def test_plan_has_no_slices_key_when_all_are_readable(self):
        run_cli(["plan", "add", "First"])
        rc, out = run_cli(["plan", "start", "S-001"])
        self.assertNotIn("slices", out)
        rc, p = run_cli(["plan"])
        self.assertNotIn("slices", p["now"])

    def test_done_without_slices(self):
        run_cli(["plan", "add", "First"])
        path = self.spec_file("S-001")
        path.write_text(path.read_text(encoding="utf-8").replace("- [ ] 1. <label> — you'll check it by <how>\n", ""), encoding="utf-8")
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
