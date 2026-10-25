"""The setup and interview skills reach a plan in four questions or fewer (FC-002 slice 3).

The new-project flow lives in `afc-setup` and the profile questions in `afc-profile`, split out of
`afc-start` and `afc-interview` by FC-009 slice 3; the assertions are unchanged.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def skill(name: str) -> str:
    return (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


class NewProjectStartTest(unittest.TestCase):
    def setUp(self):
        setup = skill("afc-setup")
        self.section = setup.split("## New project")[1].split("\n## ")[0]
        self.text = flat(self.section)

    def test_what_to_build_comes_before_the_folder(self):
        self.assertIn("What would you like to build?", self.section)
        self.assertLess(self.section.index("What would you like to build?"),
                        self.section.index("sh bin/afc defaults"))

    def test_defaults_command_is_named_and_its_fields_used(self):
        for term in ("sh bin/afc defaults", "`parent`", "`suggest_create`", "`git_name`", "`git_email`"):
            self.assertIn(term, self.text)


class InterviewTest(unittest.TestCase):
    def setUp(self):
        self.text = skill("afc-interview")
        self.profile = self.text.split("## Profile")[1].split("\n## ")[0]
        self.questions = skill("afc-profile")

    def test_just_me_means_personal_without_more_questions(self):
        flat_profile = flat(self.profile)
        self.assertIn('"Just me"', flat_profile)
        self.assertIn("sh bin/afc set profile personal", flat_profile)
        self.assertRegex(flat_profile, r"Just me.*skip every question below")




if __name__ == "__main__":
    unittest.main()
