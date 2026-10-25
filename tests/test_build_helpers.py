"""Structural checks for the lean build helpers (FC-018 slice 2)."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".claude" / "agents"
WORKFLOW = ROOT / ".claude" / "workflows" / "afc-build-spec.js"


def tools(name):
    text = (AGENTS / f"{name}.md").read_text()
    m = re.search(r"^tools:\s*(.+)$", text, re.M)
    return [t.strip() for t in m.group(1).split(",")] if m else None


class BuildHelpersTest(unittest.TestCase):
    def test_builder_names_its_tools(self):
        self.assertEqual(set(tools("afc-builder")),
                         {"Read", "Edit", "Write", "Glob", "Grep", "Bash"})

    def test_checker_cannot_edit(self):
        names = set(tools("afc-checker"))
        self.assertEqual(names, {"Read", "Glob", "Grep", "Bash"})

    def test_no_server_tools(self):
        for name in ("afc-builder", "afc-checker"):
            self.assertFalse([t for t in tools(name) if t.startswith("mcp__")])

    def test_workflow_uses_them(self):
        text = WORKFLOW.read_text()
        self.assertIn("agentType: 'afc-builder'", text)
        self.assertIn("agentType: 'afc-checker'", text)

    def test_agents_name_a_model(self):
        for name in ("afc-builder", "afc-checker", "afc-research", "afc-plan"):
            text = (AGENTS / f"{name}.md").read_text()
            self.assertRegex(text, r"model:\s+\S+")


if __name__ == "__main__":
    unittest.main()
