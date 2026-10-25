"""The right-sized test rule is written where contributors and the build skill will read it."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestRuleTest(unittest.TestCase):
    def test_contributing_tests_section_names_the_one_file_command(self):
        doc = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        section = doc.split("## Tests")[1].split("\n## ")[0]
        self.assertIn("python3 -m unittest tests.test_", section)

    def test_afc_slice_keeps_its_three_checkpoints(self):
        text = (ROOT / ".claude/skills/afc-slice/SKILL.md").read_text(encoding="utf-8")
        for n in ("1", "2", "3"):
            self.assertIn(f"## checkpoint {n}", text)
