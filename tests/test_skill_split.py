"""Situational parts of the main skills live in skills of their own, loaded only when needed
(FC-009 slice 3): setup out of start, remotes and pull requests out of deliver, the profile
questions out of interview.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"

# (new skill, skill it came out of, heading that moved, a command that moved with it)
SPLITS = [
    ("afc-setup", "afc-start", "## New project", "sh bin/afc new"),
    ("afc-setup", "afc-start", "## Existing project", "sh bin/afc adopt"),
    ("afc-remote", "afc-deliver", "## Does it need a remote?", "sh bin/afc create-remote"),
    ("afc-remote", "afc-deliver", "## Team: open a pull request", "gh pr create"),
    ("afc-profile", "afc-interview", "**Sensitive data**", "sh bin/afc set profile <profile>"),
]

# Ceilings that keep the main skills from growing back. At the first live run the four together
# were 16.3k characters; FC-001 to FC-008 took them to 22.9k.
LINE_LIMITS = {"afc-start": 55, "afc-deliver": 65, "afc-interview": 100}
MAIN_SKILLS_CHAR_LIMIT = 18000


def skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


class MovedPartsTest(unittest.TestCase):
    def test_each_new_skill_exists(self):
        for name in {s[0] for s in SPLITS}:
            self.assertTrue((SKILLS / name / "SKILL.md").is_file(), name)

    def test_the_moved_text_is_in_the_new_skill(self):
        for new, _, heading, command in SPLITS:
            text = skill(new)
            self.assertIn(heading, text, f"{new} lost {heading}")
            self.assertIn(command, text, f"{new} lost {command}")

    def test_the_moved_text_is_gone_from_the_old_skill(self):
        for _, old, heading, command in SPLITS:
            text = skill(old)
            self.assertNotIn(heading, text, f"{old} still has {heading}")
            self.assertNotIn(command, text, f"{old} still has {command}")


class PointersTest(unittest.TestCase):
    def test_each_old_skill_points_at_the_one_that_took_over(self):
        for old, new in (("afc-start", "afc-setup"), ("afc-deliver", "afc-remote"),
                         ("afc-interview", "afc-profile")):
            self.assertIn(f"`{new}`", skill(old), f"{old} does not point at {new}")

    def test_the_new_skills_hand_back_where_they_were_called_from(self):
        self.assertIn("`afc-interview`", skill("afc-setup"))
        self.assertIn("`afc-interview`", skill("afc-profile"))
        self.assertIn("`afc-deliver`", skill("afc-remote"))

    def test_claude_md_routes_each_new_skill(self):
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        for name in ("afc-setup", "afc-remote", "afc-profile"):
            self.assertIn(f"`{name}`", claude)

    def test_the_new_skills_say_when_to_use_them(self):
        for name in ("afc-setup", "afc-remote", "afc-profile"):
            text = skill(name)
            desc = next(l for l in text.splitlines() if l.startswith("description:"))
            self.assertTrue(desc.split(":", 1)[1].strip().startswith("Use when"), name)


class StaysSmallTest(unittest.TestCase):
    def test_the_trimmed_skills_stay_under_their_ceiling(self):
        for name, limit in LINE_LIMITS.items():
            self.assertLessEqual(len(skill(name).splitlines()), limit, name)

    def test_the_four_main_skills_together_stay_under_their_ceiling(self):
        total = sum(len(skill(n)) for n in ("afc-start", "afc-interview", "afc-slice", "afc-deliver"))
        self.assertLessEqual(total, MAIN_SKILLS_CHAR_LIMIT)

    def test_nothing_the_skills_ask_of_the_user_was_lost(self):
        start, setup = flat(skill("afc-start")), flat(skill("afc-setup"))
        for term in ("What would you like to build?", "OK?", "Who is it for"):
            self.assertTrue(term in setup or term in flat(skill("afc-interview")), term)
        self.assertIn("Welcome back", start)


if __name__ == "__main__":
    unittest.main()
