"""FC-026 slice 4, kept up to date by FC-029: the repo is ready for its current release."""

import re
import unittest
from pathlib import Path

from afc import version

ROOT = Path(__file__).resolve().parent.parent


def current() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


class ReadyForReleaseTest(unittest.TestCase):
    def test_version_is_v003a_or_newer(self):
        self.assertTrue(current() == "v0.03a" or version.is_newer(current(), "v0.03a"), current())

    def test_changelog_section_is_short(self):
        text = (ROOT / "docs" / "changelog.md").read_text(encoding="utf-8")
        m = re.search(rf"^## {re.escape(current())}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        self.assertIsNotNone(m)
        lines = [l for l in m.group(0).splitlines() if l.strip()]
        self.assertLessEqual(len(lines), 10)

    def test_readme_line_for_older_copies(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("v0.02a or older", text)
        self.assertIn("git pull", text)
