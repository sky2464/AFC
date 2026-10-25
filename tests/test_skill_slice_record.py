import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BY_HAND = re.compile(r"(read|edit|update|tick|write)[^.\n]*(decisions\.md|architecture\.md|spec file)", re.I)


def skill(name: str) -> str:
    return (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text()


def on_yes(text: str) -> str:
    return text.split("## On yes")[1].split("## On no")[0]


class SkillsUseSliceRecordTest(unittest.TestCase):
    def test_both_name_slice_record(self):
        for name in ("afc-slice", "afc-deliver"):
            self.assertIn("slice record", skill(name), name)

    def test_no_hand_bookkeeping(self):
        for name, text in (("afc-slice", on_yes(skill("afc-slice"))), ("afc-deliver", skill("afc-deliver"))):
            for line in text.splitlines():
                if BY_HAND.search(line):
                    self.assertRegex(line, r"(?i)never|do not", f"{name}: {line}")
            self.assertNotIn("decisions.md", text.replace("by hand", ""), name)
            self.assertNotIn("architecture.md", text, name)


if __name__ == "__main__":
    unittest.main()
