"""Role agent routing (FC-021)."""

import unittest

from afc.role_agents import (
    DEFAULT_MODELS,
    jev_config,
    parse_agent_model,
    resolve_model,
    set_agent_model,
)


class RoleAgentsTest(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(resolve_model("research", None), DEFAULT_MODELS["research"])
        self.assertEqual(resolve_model("build", None), "sonnet")

    def test_workspace_override(self):
        routing = {"roles": {"build": {"model": "claude-sonnet-4-20250514"}}}
        self.assertEqual(resolve_model("build", routing), "claude-sonnet-4-20250514")

    def test_jev_off_for_enterprise(self):
        routing = {"jev": {"enabled": True, "mode": "shadow"}}
        self.assertFalse(jev_config(routing, "enterprise")["enabled"])

    def test_frontmatter_round_trip(self):
        text = "---\nname: x\n---\nbody\n"
        out = set_agent_model(text, "haiku")
        self.assertEqual(parse_agent_model(out), "haiku")


if __name__ == "__main__":
    unittest.main()
