"""In maintenance mode the plan commands manage Flight Control's own plan (docs/), not a project's."""

import os
import re
import shutil
from pathlib import Path
from unittest.mock import patch

from afc import config, plan
from afc.config import afc_root
from tests.helpers import run_cli
from tests.test_cli import CliTestCase

SESSION = "11111111-aaaa-bbbb-cccc-000000000001"
OTHER = "22222222-aaaa-bbbb-cccc-000000000002"


class FlightControlPlanTest(CliTestCase):
    """CliTestCase gives a scratch A-FC root; docs/ in it plays Flight Control's own plan."""

    def setUp(self):
        super().setUp()
        real = afc_root()
        self.docs = self.root / "docs"
        (self.docs / "specs" / "archive").mkdir(parents=True)
        shutil.copy(real / "templates" / "workspace" / "plan" / plan.MASTER, self.docs / plan.MASTER)
        self.master = self.docs / plan.MASTER
        patcher = patch("afc.cli_plan.afc_root", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        env = patch.dict(os.environ, {"AFC_SESSION": SESSION, "CLAUDE_CODE_SESSION_ID": ""})
        env.start()
        self.addCleanup(env.stop)
        config.set_maintain(self.home, True, SESSION)

    def spec(self, sid: str) -> Path:
        return next((self.docs / "specs").glob(f"{sid}-*.md"))

    def tick_all(self, sid: str) -> None:
        path = self.spec(sid)
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(## Slices\n)", r"\1\n- [x] 1. first — you'll check it by looking\n", text, count=1)
        path.write_text(text, encoding="utf-8")

    def test_add_start_done_use_docs_and_archive_inside_specs(self):
        rc, added = run_cli(["plan", "add", "Maintenance thing", "--size", "S"])
        self.assertEqual(rc, 0, added)
        self.assertEqual(Path(added["spec"]).parent, self.docs / "specs")
        self.assertIn("| FC-001 | Maintenance thing | S | [spec](specs/FC-001-maintenance-thing.md) |",
                      self.master.read_text())
        rc, started = run_cli(["plan", "start", "FC-001"])
        self.assertEqual(rc, 0, started)
        self.tick_all("FC-001")
        rc, done = run_cli(["plan", "done", "FC-001"])
        self.assertEqual(rc, 0, done)
        archived = self.docs / "specs" / "archive" / "FC-001-maintenance-thing.md"
        self.assertTrue(archived.is_file())
        self.assertFalse(list((self.docs / "specs").glob("FC-001-*")))
        text = self.master.read_text()
        self.assertIn("[FC-001](specs/archive/FC-001-maintenance-thing.md)", text)
        index = (self.docs / "specs" / "archive" / "index.md").read_text()
        self.assertIn("FC-001-maintenance-thing.md", index)
        self.assertEqual(run_cli(["plan"])[1]["done_count"], 1)

    def test_plan_says_whose_plan_it_is(self):
        self.new("kong-gateway-lab")
        self.assertEqual(run_cli(["plan"])[1]["for"], "Flight Control")
        with patch.dict(os.environ, {"AFC_SESSION": OTHER}):
            self.assertEqual(run_cli(["plan"])[1]["for"], "kong-gateway-lab")

    def test_the_active_projects_plan_is_left_alone(self):
        _, created = self.new("kong-gateway-lab")
        project_master = Path(created["workspace_path"]) / "plan" / plan.MASTER
        before = project_master.read_text()
        run_cli(["plan", "add", "Only for Flight Control"])
        self.assertEqual(project_master.read_text(), before)
        self.assertFalse(list((Path(created["workspace_path"]) / "plan" / "specs").glob("S-*")))
        self.assertIn("Only for Flight Control", self.master.read_text())

    def test_works_with_no_project_at_all(self):
        rc, out = run_cli(["plan"])
        self.assertEqual((rc, out["for"], out["now"]), (0, "Flight Control", None))

    def test_another_session_manages_its_own_project_plan(self):
        _, created = self.new("kong-gateway-lab")
        with patch.dict(os.environ, {"AFC_SESSION": OTHER}):
            rc, out = run_cli(["plan", "add", "Project thing"])
        self.assertEqual(rc, 0, out)
        self.assertTrue(Path(out["spec"]).is_relative_to(Path(created["workspace_path"])))
        self.assertNotIn("Project thing", self.master.read_text())

    def test_ids_count_the_archive_and_never_repeat(self):
        (self.docs / "specs" / "archive" / "FC-007-old.md").write_text("# old\n")
        (self.docs / "specs" / "archive" / "S-020-project-style.md").write_text("# not ours\n")
        rc, out = run_cli(["plan", "add", "Next one"])
        self.assertEqual(out["created"], "FC-008")

    def test_project_plans_keep_s_ids(self):
        with patch.dict(os.environ, {"AFC_SESSION": OTHER}):
            self.new("kong-gateway-lab")
            self.assertEqual(run_cli(["plan", "add", "First"])[1]["created"], "S-001")

    def test_a_project_id_in_maintenance_mode_gets_a_plain_hint(self):
        run_cli(["plan", "add", "Thing"])
        rc, out = run_cli(["plan", "start", "S-001"])
        self.assertEqual(rc, 1)
        self.assertIn("S-001 is a project spec", out["error"])
        self.assertIn("maintenance mode is on", out["error"])
        self.assertEqual(run_cli(["plan", "start", "FC-001"])[1]["started"], "FC-001")

    def test_a_flight_control_id_outside_maintenance_mode_gets_a_plain_hint(self):
        self.new("kong-gateway-lab")
        with patch.dict(os.environ, {"AFC_SESSION": OTHER}):
            for command in ("start", "done"):
                rc, out = run_cli(["plan", command, "FC-003"])
                self.assertEqual(rc, 1)
                self.assertIn("FC-003 is a Flight Control spec", out["error"])
                self.assertIn("/afc mm", out["error"])

    def test_an_unknown_id_of_the_right_kind_stays_the_old_error(self):
        self.assertEqual(run_cli(["plan", "start", "FC-099"])[1]["error"],
                         "No spec FC-099 in the master plan.")

    def test_missing_master_plan_is_a_plain_error(self):
        self.master.unlink()
        rc, out = run_cli(["plan"])
        self.assertEqual(rc, 1)
        self.assertIn("Flight Control has no master plan at docs/master-plan.md", out["error"])

    def test_a_goal_that_wraps_is_read_whole(self):
        text = self.master.read_text().replace(
            "## Goal\n", "## Goal\n\nA calm co-pilot that turns what someone wants\nto build into small slices.\n\nMore detail.\n", 1)
        self.master.write_text(text)
        self.assertEqual(run_cli(["plan"])[1]["goal"],
                         "A calm co-pilot that turns what someone wants to build into small slices.")

    def test_the_real_plan_can_be_read(self):
        with patch("afc.cli_plan.afc_root", return_value=afc_root()):
            rc, out = run_cli(["plan"])
        self.assertEqual((rc, out["for"]), (0, "Flight Control"))
        self.assertTrue(out["next"] or out["now"])
