"""Compact project brief (FC-023)."""

import unittest
from pathlib import Path

from afc.context_brief import brief_path, refresh
from tests.helpers import AfcTestCase


class ContextBriefTest(AfcTestCase):
    def test_refresh_writes_brief(self):
        ws = self.home / "projects" / "demo"
        (ws / "plan").mkdir(parents=True)
        (ws / "plan" / "intent.md").write_text("# Intent\nBuild a health API.\n", encoding="utf-8")
        (ws / "agents").mkdir(parents=True)
        out = refresh(ws, profile="personal")
        path = Path(out["brief"])
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("health API", text)
        self.assertIn("research=haiku", text)
        self.assertEqual(brief_path(ws), path)


if __name__ == "__main__":
    unittest.main()
