"""Tests for swapping a project's own skills and MCP servers in and out."""

import json
from pathlib import Path

from afc import tools
from tests.helpers import run_cli
from tests.test_cli import CliTestCase


class ToolsSwapTest(CliTestCase):
    def make(self, name, skill, server):
        rc, out = self.new(name)
        self.assertEqual(rc, 0, out)
        ws = Path(out["workspace_path"])
        (ws / "skills" / skill).mkdir(parents=True)
        (ws / "skills" / skill / "SKILL.md").write_text(f"---\nname: {skill}\n---\n", encoding="utf-8")
        entry = {"command": "npx", "args": ["-y", f"{server}-mcp"], "env_keys": ["DB_URL"]}
        (ws / "mcp.json").write_text(json.dumps({"servers": {server: entry}}), encoding="utf-8")
        self.assertEqual(run_cli(["switch", name])[0], 0)  # swap in what was just added
        return ws

    def mcp(self):
        p = self.root / ".mcp.json"
        return json.loads(p.read_text(encoding="utf-8"))["mcpServers"] if p.exists() else {}

    def links(self):
        base = self.root / ".claude" / "skills"
        return sorted(p.name for p in base.glob("project-*")) if base.is_dir() else []

    def settings(self):
        return json.loads((self.root / ".claude" / "settings.local.json").read_text(encoding="utf-8"))

    def test_new_workspace_has_empty_mcp_json(self):
        _, out = self.new("alpha")
        mcp = json.loads((Path(out["workspace_path"]) / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(mcp, {"servers": {}})

    def test_switch_swaps_skills_and_servers(self):
        self.make("alpha", "a-skill", "a-db")
        self.make("beta", "b-skill", "b-db")
        self.assertEqual(self.links(), ["project-b-skill"])
        self.assertEqual(list(self.mcp()), ["b-db"])
        rc, out = run_cli(["switch", "alpha"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.links(), ["project-a-skill"])
        self.assertTrue((self.root / ".claude" / "skills" / "project-a-skill").is_symlink())
        self.assertEqual(list(self.mcp()), ["a-db"])
        self.assertEqual(self.mcp()["a-db"]["env"], {"DB_URL": "${DB_URL}"})
        self.assertEqual(self.settings()["enabledMcpjsonServers"], ["a-db"])

    def test_hand_added_server_stays(self):
        self.make("alpha", "a-skill", "a-db")
        data = json.loads((self.root / ".mcp.json").read_text(encoding="utf-8"))
        data["mcpServers"]["mine"] = {"command": "my-tool"}
        (self.root / ".mcp.json").write_text(json.dumps(data), encoding="utf-8")
        self.make("beta", "b-skill", "b-db")
        self.assertEqual(sorted(self.mcp()), ["b-db", "mine"])

    def test_pause_clears_and_resume_restores(self):
        self.make("alpha", "a-skill", "a-db")
        rc, out = run_cli(["pause", "alpha"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.links(), [])
        self.assertEqual(self.mcp(), {})
        self.assertNotIn("enabledMcpjsonServers", self.settings())
        rc, out = run_cli(["resume", "alpha"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.links(), ["project-a-skill"])
        self.assertEqual(list(self.mcp()), ["a-db"])

    def test_remove_active_clears(self):
        self.make("alpha", "a-skill", "a-db")
        rc, out = run_cli(["remove", "alpha"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.links(), [])
        self.assertEqual(self.mcp(), {})

    def test_literal_token_is_refused_and_switch_rolls_back(self):
        self.make("alpha", "a-skill", "a-db")
        ws = self.make("beta", "b-skill", "b-db")
        run_cli(["switch", "alpha"])
        self.assertEqual(list(self.mcp()), ["a-db"])
        bad = {"command": "npx", "args": ["--token=abcdefghijklmnop1234"]}
        (ws / "mcp.json").write_text(json.dumps({"servers": {"b-db": bad}}), encoding="utf-8")
        rc, out = run_cli(["switch", "beta"])
        self.assertNotEqual(rc, 0)
        self.assertIn("secret", out["error"])
        self.assertEqual(list(self.mcp()), ["a-db"])
        self.assertEqual(self.links(), ["project-a-skill"])

    def test_env_with_values_is_refused(self):
        ws = self.make("alpha", "a-skill", "a-db")
        entry = {"command": "npx", "env": {"DB_URL": "postgres://u:pw@host/db"}}
        (ws / "mcp.json").write_text(json.dumps({"servers": {"a-db": entry}}), encoding="utf-8")
        with self.assertRaises(tools.ToolsError) as ctx:
            tools.swap_in(self.root, ws)
        self.assertIn("env_keys", str(ctx.exception))
