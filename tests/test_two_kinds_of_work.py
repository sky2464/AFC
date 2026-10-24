"""Claude is told there are two kinds of work, to ask when a request is unclear, never to create
branches in an app, and to prove an undo."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """The text on one line, so a phrase that wraps in the file still matches."""
    return " ".join(text.split())


class TwoKindsOfWorkTest(unittest.TestCase):
    def setUp(self):
        self.claude = read("CLAUDE.md")
        self.section = self.claude.split("## Two kinds of work")[1].split("\n## ")[0]
        self.text = flat(self.section)

    def test_section_names_both_kinds_and_how_to_tell(self):
        self.assertIn("## Two kinds of work", self.claude)
        for term in ("active project", "Flight Control itself", "maintenance mode", "`/afc mm`",
                     "`/afc mm off`", "docs/master-plan.md", "`FC-001`", "`S-001`", "Mode: maintenance"):
            self.assertIn(term, self.text)

    def test_section_comes_early_and_stays_short(self):
        self.assertLess(self.claude.index("## Two kinds of work"), self.claude.index("## Simple by default"))
        self.assertLessEqual(len(self.claude.splitlines()), 120)
        self.assertLessEqual(len(self.section.splitlines()), 30)

    def test_wrong_kind_of_request_has_a_plain_answer(self):
        self.assertRegex(self.text, r"build FC-.*maintenance mode is off")
        self.assertRegex(self.text, r"build S-.*maintenance mode is on.*projects are set aside")
        self.assertIn("do not touch the active project", self.text)

    def test_ask_first_when_a_request_is_unclear(self):
        self.assertIn("Stop and ask one question, and build nothing", self.text)
        for term in ("isn't in the plan you are working in", "a branch that doesn't exist", "either kind of work"):
            self.assertIn(term, self.text)

    def test_two_problems_get_one_question_and_a_leftover_gets_asked_about(self):
        self.assertIn("ask about the first one only", self.text)
        self.assertIn("If anything is left, say what it is and ask before removing it", self.text)

    def test_no_branches_in_apps(self):
        self.assertIn("Never create a branch in a user's app", self.text)
        for term in ("git switch -c", "git checkout -b", "sh bin/afc deliver"):
            self.assertIn(term, self.text)

    def test_undo_is_proved(self):
        self.assertIn("git status --short", self.text)
        self.assertIn("before saying it is clean", self.text)


class SkillsFollowTheSameRulesTest(unittest.TestCase):
    def setUp(self):
        self.slice = read(".claude/skills/afc-slice/SKILL.md")

    def test_slice_skill_asks_before_building_the_wrong_spec(self):
        text = flat(self.slice)
        self.assertIn("not the active one", text)
        self.assertIn("do not start it and do not build anything", text)

    def test_slice_skill_widens_the_rule_to_ids_and_branches(self):
        text = flat(self.slice)
        for term in ("isn't in the plan from `sh bin/afc plan`", "`FC-` ID", "branch that doesn't exist",
                     "never create a branch in the app"):
            self.assertIn(term, text)

    def test_slice_skill_proves_an_undo(self):
        on_no = flat(self.slice.split("## On no")[1])
        self.assertIn("git status --short", on_no)
        self.assertIn("before saying it is clean", on_no)

    def test_skills_stay_within_their_size_limit(self):
        for path in (ROOT / ".claude" / "skills").glob("*/SKILL.md"):
            self.assertLessEqual(len(path.read_text(encoding="utf-8").splitlines()), 250, path.parent.name)

    def test_commit_text_does_not_ask_for_a_branch(self):
        deliver = read(".claude/skills/afc-deliver/SKILL.md")
        self.assertNotRegex(deliver, re.compile(r"git (switch -c|checkout -b)"))


if __name__ == "__main__":
    unittest.main()
