"""Per-project agent install (FC-022)."""

import json
import unittest
from pathlib import Path

from afc.project_agents import install_code_agents
from afc.registry import Project
from afc.role_agents import parse_agent_model
from tests.helpers import AfcTestCase


class ProjectAgentsTest(AfcTestCase):
    def test_install_writes_agents_and_routing(self):
        code = self.tmp / "app"
        code.mkdir()
        ws = self.home / "projects" / "demo"
        ws.mkdir(parents=True)
        result = install_code_agents(code, ws, "personal")
        agents = Path(result["agents_dir"])
        self.assertTrue((agents / "afc-build.md").is_file())
        model = parse_agent_model((agents / "afc-build.md").read_text(encoding="utf-8"))
        self.assertEqual(model, "sonnet")
        routing = json.loads((ws / "agents" / "routing.json").read_text(encoding="utf-8"))
        self.assertFalse(routing["jev"]["enabled"])
        self.assertTrue((code / ".claude" / "workflows" / "afc-build-slice.js").is_file())


if __name__ == "__main__":
    unittest.main()
