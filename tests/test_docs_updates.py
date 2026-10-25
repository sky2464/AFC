"""README and CONTRIBUTING describe the update offer and the release steps (FC-011 slice 7)."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def flat(text: str) -> str:
    return " ".join(text.split())


class ReadmeUpdateTest(unittest.TestCase):
    def setUp(self):
        self.text = flat((ROOT / "README.md").read_text(encoding="utf-8"))

    def test_no_manual_git_pull_to_update(self):
        self.assertNotIn("run `git pull`", self.text)

    def test_describes_the_update_offer(self):
        for term in ("Update now", "Not now", "newer release", "claude --continue", "/exit"):
            self.assertIn(term, self.text)


class ContributingReleaseTest(unittest.TestCase):
    def setUp(self):
        doc = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("## Releasing", doc)
        self.section = flat(doc.split("## Releasing")[1].split("\n## ")[0])

    def test_release_steps_include_version_bump(self):
        for term in ("`VERSION`", "tag", "`main`"):
            self.assertIn(term, self.section)

    def test_release_steps_include_workspace_upgrade_step(self):
        for term in ("afc/upgrade_", "run(home)", "layout"):
            self.assertIn(term, self.section)


if __name__ == "__main__":
    unittest.main()
