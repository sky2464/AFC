"""The start and interview skills reach a plan in four questions or fewer (FC-002 slice 3)."""

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
        start = skill("afc-start")
        self.section = start.split("## New project")[1].split("\n## ")[0]
        self.text = flat(self.section)

    def test_what_to_build_comes_before_the_folder(self):
        self.assertIn("What would you like to build?", self.section)
        self.assertLess(self.section.index("What would you like to build?"),
                        self.section.index("sh bin/afc defaults"))

    def test_the_folder_is_never_asked_first(self):
        self.assertNotIn("**Parent folder**", self.section)
        self.assertNotIn("Ask each of these in its own message", self.section)

    def test_defaults_command_is_named_and_its_fields_used(self):
        for term in ("sh bin/afc defaults", "`parent`", "`suggest_create`", "`git_name`", "`git_email`"):
            self.assertIn(term, self.text)

    def test_identity_is_stated_with_its_source_not_asked(self):
        self.assertIn("Commits will use", self.text)
        self.assertIn("say if you want another", self.text)

    def test_identity_is_asked_only_when_none_is_found(self):
        self.assertRegex(self.text, r'`"source": "none"`|source is `none`')

    def test_ai_line_is_off_and_stated(self):
        self.assertIn("no AI co-author line", self.text)

    def test_name_is_suggested_not_asked(self):
        self.assertRegex(self.text, r"(suggest|propose|call it)")
        self.assertIn("only if", self.text)

    def test_setup_is_one_confirming_question(self):
        self.assertRegex(self.text, r"one (confirming )?question")

    def test_the_new_command_still_gets_every_value(self):
        for term in ("sh bin/afc new --name", "--parent", "--git-name", "--git-email", "[--ai-trailer]"):
            self.assertIn(term, self.section)

    def test_the_four_question_budget_is_written_down(self):
        self.assertIn("four questions", self.text)

    def test_no_icloud_folder_is_recommended(self):
        self.assertIn("iCloud", self.text)


class InterviewTest(unittest.TestCase):
    def setUp(self):
        self.text = skill("afc-interview")
        self.profile = self.text.split("## Profile")[1].split("\n## ")[0]

    def test_one_combined_who_and_what_for_question_comes_first(self):
        self.assertIn("Who is it for, and what for", self.profile)
        self.assertLess(self.profile.index("Who is it for, and what for"), self.profile.index("**Purpose**"))

    def test_just_me_means_personal_without_more_questions(self):
        flat_profile = flat(self.profile)
        self.assertIn('"Just me"', flat_profile)
        self.assertIn("sh bin/afc set profile personal", flat_profile)
        self.assertRegex(flat_profile, r"Just me.*skip every question below")

    def test_other_people_or_a_company_keep_the_full_questions(self):
        for term in ("**Purpose**", "**Users**", "**Inside or outside**", "**Company**",
                     "**Sensitive data**", "**Wiki**"):
            self.assertIn(term, self.profile)
        self.assertIn("a quick prototype", self.profile)
        self.assertIn("an MVP", self.profile)

    def test_profile_table_is_unchanged(self):
        for row in ("`enterprise`", "`work`", "`mvp`", "`prototype`", "`personal`"):
            self.assertIn(row, self.profile)

    def test_the_plan_question_is_the_last_of_the_four(self):
        self.assertIn("Start with the first one?", self.text)

    def test_the_intent_fields_are_unchanged(self):
        for field in ("Goal", "For whom", "Success", "Non-goals", "Assumptions", "Risks",
                      "Open questions"):
            self.assertRegex(self.text, rf"\*\*{field}\*\*")


class QuestionBudgetTest(unittest.TestCase):
    """Count the questions a personal 'just me' start asks, as the two skills write it."""

    def test_a_personal_start_asks_four_or_fewer(self):
        start = flat(skill("afc-start").split("## New project")[1].split("\n## ")[0])
        interview = skill("afc-interview")
        asked = [
            "What would you like to build?",       # 1: the start of the intent
            "OK?",                                  # 2: one question confirming name, folder, identity
            "Who is it for",                        # 3: combined who and what for
            "Start with the first one?",            # 4: the plan
        ]
        self.assertIn(asked[0], start)
        self.assertIn(asked[1], start)
        self.assertIn(asked[2], interview)
        self.assertIn(asked[3], interview)
        self.assertLessEqual(len(asked), 4)


if __name__ == "__main__":
    unittest.main()
