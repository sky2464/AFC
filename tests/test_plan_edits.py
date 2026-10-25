"""Plan and spec edits change only the lines that change (FC-017 slice 2)."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def skill(name: str) -> str:
    return " ".join((ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8").split()).lower()


class ChangedLinesOnlyTest(unittest.TestCase):
    def test_slice_skill_edits_changed_lines_only(self):
        text = skill("afc-slice").split("## on yes")[1].split("## on no")[0]
        self.assertIn("change only the lines that change", text)
        self.assertIn("never rewrite a whole file", text)

    def test_drift_skill_edits_changed_lines_only(self):
        text = skill("afc-drift")
        self.assertIn("change only the lines that change", text)
        self.assertIn("never rewrite a whole file", text)


if __name__ == "__main__":
    unittest.main()
