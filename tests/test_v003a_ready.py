"""FC-026 slice 4: the repo is ready for v0.03a."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ReadyForV003aTest(unittest.TestCase):
    def test_version_says_v003a(self):
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8").strip(), "v0.03a")

    def test_changelog_section_is_short(self):
        text = (ROOT / "docs" / "changelog.md").read_text(encoding="utf-8")
        m = re.search(r"^## v0\.03a\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        self.assertIsNotNone(m)
        lines = [l for l in m.group(0).splitlines() if l.strip()]
        self.assertLessEqual(len(lines), 10)

    def test_readme_line_for_older_copies(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("v0.02a or older", text)
        self.assertIn("git pull", text)
