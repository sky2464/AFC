"""Role agents and per-role model routing (FC-021).

Roles are research, plan, build and check. Each maps to a Claude Code agent file with an explicit
``model`` in frontmatter. Per-project overrides live in the workspace routing file; the main
session is never given a Haiku default here.
"""

import json
import re
from pathlib import Path

ROLES = ("research", "plan", "build", "check")

# Project slice agents (in the app's .claude/agents/).
PROJECT_AGENT = {
    "research": "afc-research",
    "plan": "afc-plan",
    "build": "afc-build",
    "check": "afc-check",
}

# Maintenance spec-build agents (in the Flight Control repo).
MAINTENANCE_AGENT = {
    "research": "afc-research",
    "plan": "afc-plan",
    "build": "afc-builder",
    "check": "afc-checker",
}

DEFAULT_MODELS = {
    "research": "haiku",
    "plan": "opus",
    "build": "sonnet",
    "check": "haiku",
}

CHECK_MODEL_ALT = "sonnet"

ROUTING_NAME = "routing.json"
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MODEL_LINE = re.compile(r"^model:\s*(\S+)\s*$", re.M)


def routing_path(workspace: Path) -> Path:
    return Path(workspace) / "agents" / ROUTING_NAME


def load_routing(workspace: Path) -> dict:
    """Return routing dict; missing file means defaults only."""
    path = routing_path(workspace)
    if not path.is_file():
        return {"roles": {}, "notes": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"roles": {}, "notes": {}}
    if not isinstance(data, dict):
        return {"roles": {}, "notes": {}}
    roles = data.get("roles")
    if not isinstance(roles, dict):
        roles = {}
    notes = data.get("notes")
    if not isinstance(notes, dict):
        notes = {}
    return {"roles": roles, "notes": notes}


def resolve_model(role: str, routing: dict | None, *, profile: str = "personal") -> str:
    """Model name for a role after defaults and workspace overrides."""
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    base = DEFAULT_MODELS[role]
    if routing:
        entry = routing.get("roles", {}).get(role)
        if isinstance(entry, dict) and isinstance(entry.get("model"), str) and entry["model"].strip():
            base = entry["model"].strip()
        elif isinstance(entry, str) and entry.strip():
            base = entry.strip()
    if role == "check" and base == "sonnet":
        return CHECK_MODEL_ALT
    return base


def jev_config(routing: dict | None, profile: str) -> dict:
    """Jev is always off for enterprise; otherwise read routing (default off)."""
    off = {"enabled": False, "mode": "off"}
    if profile == "enterprise":
        return off
    if not routing:
        return off
    jev = routing.get("jev")
    if not isinstance(jev, dict):
        return off
    enabled = bool(jev.get("enabled"))
    mode = jev.get("mode") if jev.get("mode") in ("shadow", "off") else "off"
    if not enabled:
        mode = "off"
    return {"enabled": enabled, "mode": mode, "model": jev.get("model") or "jev-latest"}


def parse_agent_model(text: str) -> str | None:
    m = FRONTMATTER.match(text)
    if not m:
        return None
    found = MODEL_LINE.search(m.group(1))
    return found.group(1) if found else None


def set_agent_model(text: str, model: str) -> str:
    """Insert or replace model: in YAML frontmatter."""
    m = FRONTMATTER.match(text)
    if not m:
        return text
    body = m.group(1)
    if MODEL_LINE.search(body):
        body = MODEL_LINE.sub(f"model: {model}", body, count=1)
    else:
        body = body.rstrip() + f"\nmodel: {model}\n"
    return f"---\n{body}\n---\n{text[m.end():]}"


def routing_summary(routing: dict | None, profile: str) -> dict:
    """Resolved models per role for CLI output."""
    routing = routing or {"roles": {}, "notes": {}}
    return {
        "roles": {role: resolve_model(role, routing, profile=profile) for role in ROLES},
        "defaults": dict(DEFAULT_MODELS),
        "jev": jev_config(routing, profile),
        "provider_note": (
            "Bedrock and Vertex need full model IDs in workspace agents/routing.json. "
            "Claude Haiku 5.5 needs Claude Code >= v2.1.293."
        ),
    }
