"""Finishing a spec tells the user what shipped and what is next (FC-015 slice 5)."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = " ".join((ROOT / ".claude/skills/afc-slice/SKILL.md").read_text(encoding="utf-8").split())
FINISH = TEXT.split("`sh bin/afc plan done <id>`")[1]


class ShipFlowTest(unittest.TestCase):
    def test_two_plain_lines_what_shipped_and_what_is_next(self):
        self.assertIn("two plain lines", FINISH)
        self.assertIn("what shipped", FINISH)
        self.assertIn("what is next", FINISH)

    def test_next_spec_is_step_one(self):
        self.assertIn("suggest_next", FINISH)
        self.assertIn("numbered step 1", FINISH)

    def test_refusal_is_relayed_not_worked_around(self):
        self.assertIn("Not ready", FINISH)
        self.assertIn("never deploy", FINISH)

    def test_gate_can_be_checked_first(self):
        self.assertIn("sh bin/afc ship --check <id>", TEXT)


if __name__ == "__main__":
    unittest.main()
