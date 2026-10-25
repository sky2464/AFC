"""Tests for the FC-015 changelog: `plan done` writes one readable entry per finished spec."""

import os
import shutil
from pathlib import Path
from unittest.mock import patch

from afc import config, plan
from afc.config import afc_root
from tests.helpers import run_cli
from tests.test_cli import CliTestCase

SESSION = "11111111-aaaa-bbbb-cccc-000000000001"

SPEC_BODY = """## Goal

Say what shipped in
words a person can read.

More detail nobody needs.

## Slices

- [x] 1. The first part — you'll check it by looking (tests)
- [x] 2. The second part — you'll check it by running it

## Decisions
"""


def _finish_ready(testcase):
    for name in ("tests_green", "clean_tree"):
        patcher = patch(f"afc.ship.{name}", return_value=[])
        patcher.start()
        testcase.addCleanup(patcher.stop)


def _fill(path: Path, title: str) -> None:
    head = path.read_text(encoding="utf-8").split("## Goal")[0]
    path.write_text(head + SPEC_BODY, encoding="utf-8")


class ProjectChangelogTest(CliTestCase):
    def setUp(self):
        super().setUp()
        rc, out = self.new()
        self.assertEqual(rc, 0)
        self.ws = Path(out["workspace_path"])
        _finish_ready(self)

    def finish(self, title, day):
        run_cli(["plan", "add", title])
        sid = run_cli(["plan"])[1]["next"][0]["id"]
        run_cli(["plan", "start", sid])
        _fill(next((self.ws / "plan" / "specs").glob(f"{sid}-*.md")), title)
        with patch("afc.cli._today", return_value=day):
            rc, out = run_cli(["plan", "done", sid])
        self.assertEqual(rc, 0, out)
        return sid

    def test_entry_has_date_goal_and_slices_in_plain_words(self):
        self.finish("Thing", "2026-10-25")
        text = (self.ws / "changelog.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Changelog\n"))
        self.assertIn("## 2026-10-25 — S-001 Thing", text)
        self.assertIn("Say what shipped in words a person can read.", text)
        self.assertNotIn("More detail", text)
        self.assertIn("- The first part\n- The second part", text)
        self.assertNotIn("you'll check", text)

    def test_one_entry_per_spec_newest_first(self):
        self.finish("First", "2026-10-24")
        self.finish("Second", "2026-10-25")
        text = (self.ws / "changelog.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("\n## "), 2)
        self.assertLess(text.index("S-002 Second"), text.index("S-001 First"))
        self.assertEqual(text.count("# Changelog"), 1)

    def test_a_refused_finish_writes_no_changelog(self):
        run_cli(["plan", "add", "Thing"])
        run_cli(["plan", "start", "S-001"])
        rc, _ = run_cli(["plan", "done", "S-001"])
        self.assertEqual(rc, 1)
        self.assertFalse((self.ws / "changelog.md").exists())


class FlightControlChangelogTest(CliTestCase):
    def setUp(self):
        super().setUp()
        self.docs = self.root / "docs"
        (self.docs / "specs" / "archive").mkdir(parents=True)
        shutil.copy(afc_root() / "templates" / "workspace" / "plan" / plan.MASTER, self.docs / plan.MASTER)
        patcher = patch("afc.cli_plan.afc_root", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        _finish_ready(self)
        env = patch.dict(os.environ, {"AFC_SESSION": SESSION, "CLAUDE_CODE_SESSION_ID": ""})
        env.start()
        self.addCleanup(env.stop)
        config.set_maintain(self.home, True, SESSION)

    def test_flight_controls_own_plan_gets_an_entry(self):
        run_cli(["plan", "add", "Maintenance thing"])
        run_cli(["plan", "start", "FC-001"])
        _fill(next((self.docs / "specs").glob("FC-001-*.md")), "x")
        with patch("afc.cli._today", return_value="2026-10-25"):
            rc, out = run_cli(["plan", "done", "FC-001"])
        self.assertEqual(rc, 0, out)
        text = (self.docs / "changelog.md").read_text(encoding="utf-8")
        self.assertIn("## 2026-10-25 — FC-001 Maintenance thing", text)
        self.assertIn("- The second part", text)
