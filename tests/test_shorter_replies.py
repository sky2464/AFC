"""Shorter replies and skill text: each step said once (FC-017 slice 3)."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return " ".join((ROOT / path).read_text(encoding="utf-8").split()).lower()


class ShorterRepliesTest(unittest.TestCase):
    def test_build_replies_are_a_status_line_and_one_question(self):
        text = read(".claude/skills/afc-slice/SKILL.md")
        self.assertIn("a status line and at most one question", text)
        self.assertIn("do not restate the plan", text)

    def test_slice_skill_states_each_step_once(self):
        text = read(".claude/skills/afc-slice/SKILL.md")
        self.assertEqual(text.count("elevation of privilege"), 1)
        self.assertEqual(text.count("never use `cat`"), 0)
        self.assertNotIn("one question at a time", text)

    def test_slice_skill_is_smaller(self):
        size = len((ROOT / ".claude/skills/afc-slice/SKILL.md").read_text(encoding="utf-8"))
        self.assertLess(size, 7300)

    def test_threat_check_table_lives_in_the_skill_only(self):
        rule = read("rules/architecture.md")
        self.assertNotIn("| threat | category | mitigation |", rule)
        self.assertIn("mini threat check", rule)
        self.assertIn("never write a full stride document", rule)
        self.assertIn("| threat | category | mitigation |", read(".claude/skills/afc-slice/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
