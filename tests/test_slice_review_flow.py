"""The slice flow reviews before asking for approval (FC-014 slice 5)."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = (ROOT / ".claude/skills/afc-slice/SKILL.md").read_text(encoding="utf-8")


def section(n: int) -> str:
    return " ".join(TEXT.split("## checkpoint %d" % n)[1].split("\n## ")[0].split())


class SliceReviewFlowTest(unittest.TestCase):
    def test_checkpoint_3_runs_review_before_asking(self):
        s = section(3)
        self.assertIn('sh bin/afc review --slice "<n> <label>"', s)
        self.assertLess(s.index("afc review"), s.index("Is this what you meant?"))

    def test_blocked_verdict_stops_the_approval_question(self):
        s = section(3)
        self.assertIn("blocked", s)
        self.assertIn("do not ask", s.lower())

    def test_checkpoint_2_has_the_root_cause_rule(self):
        s = section(2)
        for part in ("hypothesis", "reproduction test", "three"):
            self.assertIn(part, s)


if __name__ == "__main__":
    unittest.main()
