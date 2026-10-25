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
        self.assertIn("sh bin/afc home set", self.text)
        self.assertIn("no home set uses your real `~/.A-FC`", self.text)

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


class TestCopySetupTest(unittest.TestCase):
    """The setup a developer follows on a fresh test copy (FC-001 slice 4)."""

    def setUp(self):
        self.doc = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.setup = flat(self.doc.split("## Set up")[1].split("\n## ")[0])

    def test_set_up_clones_both_copies(self):
        for folder in ("A-FC-dev", "A-FC-test"):
            self.assertIn(f"git clone https://github.com/sky2464/AFC.git {folder}", self.setup)

    def test_set_up_gives_the_test_copy_its_own_home(self):
        for step in ("AFC_HOME=~/A-FC-test-home sh bin/afc maintain on",
                     "AFC_HOME=~/A-FC-test-home sh bin/afc home set ~/A-FC-test-home",
                     "sh bin/afc maintain off"):
            self.assertIn(step, self.setup)

    def test_set_up_says_a_fresh_clone_uses_the_real_home(self):
        self.assertIn("A fresh clone uses your real `~/.A-FC` until you do", self.setup)

    def test_set_up_names_the_check_and_the_way_back(self):
        self.assertIn('`sh bin/afc home` should answer `"source": "file"`', self.setup)
        self.assertIn("sh bin/afc home clear", self.setup)

    def test_set_up_explains_the_home_file_and_git(self):
        self.assertIn("`.afc-home`", self.setup)
        self.assertIn("git-ignored", self.setup)
        self.assertIn("needs maintenance", self.setup)

    def test_the_old_prefix_every_time_instruction_is_gone(self):
        self.assertNotIn("AFC_HOME=~/A-FC-test-home claude", self.doc)

    def test_changing_the_home_needs_maintenance_mode(self):
        editing = flat(self.doc.split("## Editing Flight Control itself")[1].split("\n## ")[0])
        self.assertIn("sh bin/afc home set", editing)
        self.assertIn("sh bin/afc home clear", editing)
        self.assertIn("need maintenance mode", editing)

    def test_readme_sends_a_second_copy_to_contributing(self):
        readme = flat((ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("second copy", readme)
        self.assertIn("CONTRIBUTING.md", readme)
        self.assertIn("workspace of its own", readme)


if __name__ == "__main__":
    unittest.main()
