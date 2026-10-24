"""CONTRIBUTING.md says where to work so Flight Control work and real use never get mixed up."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def flat(text: str) -> str:
    return " ".join(text.split())


class ThreePlacesTest(unittest.TestCase):
    def setUp(self):
        self.doc = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.places = self.doc.split("## Three places to work")[1].split("\n## ")[0]
        self.text = flat(self.places)

    def test_section_exists_and_comes_before_the_tests_section(self):
        self.assertIn("## Three places to work", self.doc)
        self.assertLess(self.doc.index("## Three places to work"), self.doc.index("## Tests"))

    def test_names_all_three_places_with_their_branch_and_mode(self):
        table = [line for line in self.places.splitlines() if line.startswith("|")]
        self.assertEqual(len(table), 5)  # header, divider, three places
        joined = flat(" ".join(table))
        for term in ("Daily folder", "Developer copy", "Test copy", "`main`", "`dev`", "/afc mm"):
            self.assertIn(term, joined)

    def test_keeps_flight_control_work_and_project_work_apart(self):
        for term in ("`FC-001`", "`S-001`", "never in the daily folder", "🔧"):
            self.assertIn(term, self.text)
        self.assertRegex(self.text, r"project work.*never.*developer copy")

    def test_test_copy_must_use_its_own_home(self):
        self.assertIn("`AFC_HOME`", self.text)
        self.assertIn("never in your real `~/.A-FC`", self.text)

    def test_rollout_order_is_written_down(self):
        self.assertIn("update the daily folder first", self.text)
        self.assertIn("session flag", self.text)
        self.assertIn("git pull", self.text)

    def test_maintenance_mode_is_per_session(self):
        editing = flat(self.doc.split("## Editing Flight Control itself")[1].split("\n## ")[0])
        for term in ("this session only", "/afc mm", "sh bin/afc maintain on", "sh bin/afc maintain off"):
            self.assertIn(term, editing)

    def test_old_clone_advice_is_gone(self):
        self.assertNotIn("not in the `A-FC` folder you use day to day", self.doc)

    def test_every_listed_branch_exists_in_the_plan_text(self):
        self.assertRegex(self.doc, re.compile(r"`main` holds released versions"))
        self.assertRegex(self.doc, re.compile(r"`dev` is where ongoing work lands"))


if __name__ == "__main__":
    unittest.main()
