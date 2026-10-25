"""afc.rules: the short form of a rule module is its Do and Never sections, nothing else."""

import tempfile
import unittest
from pathlib import Path

from afc import rules

LONG = """# Input

## Applies when
- The slice reads anything from outside.

## Do
- Validate every input.

## Never
- Never trust the client alone.

## Check
- Tests: one valid and one malicious value.
"""


class ShortFormTest(unittest.TestCase):
    def test_keeps_title_do_and_never(self):
        self.assertEqual(
            rules.short_form(LONG),
            "# Input\n\n## Do\n- Validate every input.\n\n## Never\n- Never trust the client alone.\n",
        )

    def test_drops_applies_when_and_check(self):
        short = rules.short_form(LONG)
        self.assertNotIn("Applies when", short)
        self.assertNotIn("## Check", short)

    def test_is_stable_when_applied_twice(self):
        once = rules.short_form(LONG)
        self.assertEqual(rules.short_form(once), once)

    def test_a_missing_section_is_an_error_not_a_silent_loss(self):
        for gone in ("## Do\n- Validate every input.\n\n", "## Never\n- Never trust the client alone.\n\n"):
            with self.assertRaises(ValueError):
                rules.short_form(LONG.replace(gone, ""))


class WriteShortTest(unittest.TestCase):
    def test_writes_one_short_file_per_rule_and_leaves_the_long_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rules").mkdir()
            (root / "rules" / "input.md").write_text(LONG, encoding="utf-8")
            written = rules.write_short(root)
            self.assertEqual([p.name for p in written], ["input.md"])
            self.assertEqual((root / "rules" / "short" / "input.md").read_text(encoding="utf-8"),
                             rules.short_form(LONG))
            self.assertEqual((root / "rules" / "input.md").read_text(encoding="utf-8"), LONG)

    def test_removes_a_short_file_whose_long_form_is_gone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rules" / "short").mkdir(parents=True)
            (root / "rules" / "short" / "old.md").write_text("# Old\n", encoding="utf-8")
            rules.write_short(root)
            self.assertFalse((root / "rules" / "short" / "old.md").exists())


if __name__ == "__main__":
    unittest.main()
