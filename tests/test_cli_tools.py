"""Tests for `afc tools` and `afc tools add`."""

import json
from pathlib import Path

from tests.helpers import run_cli
from tests.test_cli import CliTestCase


class ToolsCommandTest(CliTestCase):
    def setUp(self):
        super().setUp()
        lib = self.root / "library"
        (lib / "skills" / "lib-skill").mkdir(parents=True)
        (lib / "skills" / "lib-skill" / "SKILL.md").write_text("---\nname: lib-skill\n---\n", encoding="utf-8")
        (lib / "mcp").mkdir()
        recipe = {"command": "npx", "args": ["-y", "tickets-mcp"], "env_keys": ["TICKETS_TOKEN"],
                  "description": "Tickets", "publisher": "Example Co", "vetted": "2026-10-23"}
        (lib / "mcp" / "tickets.json").write_text(json.dumps(recipe), encoding="utf-8")

    def ws(self, out):
        return Path(out["workspace_path"])

    def test_list_shows_project_and_library(self):
        self.new("alpha")
        rc, out = run_cli(["tools"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out, {"project": {"skills": [], "servers": []},
                               "library": {"skills": ["lib-skill"], "servers": ["tickets"]}})

    def test_add_skill(self):
        _, new = self.new("alpha")
        rc, out = run_cli(["tools", "add", "lib-skill"])
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.ws(new) / "skills" / "lib-skill" / "SKILL.md").is_file())
        self.assertTrue((self.root / ".claude" / "skills" / "project-lib-skill").exists())
        self.assertEqual(run_cli(["tools"])[1]["project"]["skills"], ["lib-skill"])

    def test_add_server(self):
        _, new = self.new("alpha")
        rc, out = run_cli(["tools", "add", "tickets"])
        self.assertEqual(rc, 0, out)
        saved = json.loads((self.ws(new) / "mcp.json").read_text(encoding="utf-8"))["servers"]["tickets"]
        self.assertEqual(saved["env_keys"], ["TICKETS_TOKEN"])
        self.assertNotIn("publisher", saved)
        live = json.loads((self.root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        self.assertEqual(live["tickets"]["env"], {"TICKETS_TOKEN": "${TICKETS_TOKEN}"})
        self.assertEqual(run_cli(["tools"])[1]["project"]["servers"], ["tickets"])

    def test_unknown_name(self):
        self.new("alpha")
        rc, out = run_cli(["tools", "add", "nope"])
        self.assertNotEqual(rc, 0)
        self.assertIn("nope", out["error"])

    def test_already_there(self):
        self.new("alpha")
        run_cli(["tools", "add", "tickets"])
        rc, out = run_cli(["tools", "add", "tickets"])
        self.assertNotEqual(rc, 0)
        self.assertIn("already", out["error"])

    def test_no_active_project(self):
        rc, out = run_cli(["tools", "add", "tickets"])
        self.assertNotEqual(rc, 0)
        self.assertIn("error", out)
        rc, out = run_cli(["tools"])
        self.assertNotEqual(rc, 0)

    def test_bad_recipe_changes_nothing(self):
        _, new = self.new("alpha")
        bad = {"command": "npx", "args": [], "env": {"X": "y"}}
        (self.root / "library" / "mcp" / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
        rc, out = run_cli(["tools", "add", "bad"])
        self.assertNotEqual(rc, 0)
        saved = json.loads((self.ws(new) / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, {"servers": {}})
