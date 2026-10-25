"""CONTRIBUTING.md says where to work so Flight Control work and real use never get mixed up."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def flat(text: str) -> str:
    return " ".join(text.split())


class ThreePlacesTest(unittest.TestCase):
    def setUp(self):
        self.doc = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.places = self.doc.split("## Three places to work")[1].split("\n## ")[0]
        self.text = flat(self.places)

    def test_section_exists_and_comes_before_the_tests_section(self):
        self.assertIn("## Three places to work", self.doc)
        self.assertLess(self.doc.index("## Three places to work"), self.doc.index("## Tests"))




if __name__ == "__main__":
    unittest.main()
