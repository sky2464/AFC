"""Role agents and per-role model routing (FC-021, FC-050).

Roles are research, plan, build, check, architect and docs. Each maps to a Claude Code agent file
with explicit ``model`` and optional ``effort`` in frontmatter. Per-project overrides live in the
workspace routing file; the main session is never given a Haiku default here.
"""

import json
import re
from pathlib import Path

ROLES = ("research", "plan", "build", "check", "architect", "docs")

# Project slice agents (in the app's .claude/agents/).
PROJECT_AGENT = {
    "research": "afc-research",
    "plan": "afc-plan",
    "build": "afc-build",
    "check": "afc-check",
    "architect": "afc-architect",
    "docs": "afc-docs",
}

# Maintenance spec-build agents (in the Flight Control repo).
MAINTENANCE_AGENT = {
    "research": "afc-research",
    "plan": "afc-plan",
    "build": "afc-builder",
    "check": "afc-checker",
    "architect": "afc-architect",
    "docs": "afc-docs",
}

DEFAULT_MODELS = {
    "research": "haiku",
    "plan": "opus",
    "build": "sonnet",
    "check": "haiku",
    "architect": "opus",
    "docs": "haiku",
}

DEFAULT_EFFORT = {
    "architect": "high",
    "docs": "low",
}

CHECK_MODEL_ALT = "sonnet"

ROUTING_NAME = "routing.json"
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MODEL_LINE = re.compile(r"^model:\s*(\S+)\s*$", re.M)
EFFORT_LINE = re.compile(r"^effort:\s*(\S+)\s*$", re.M)

ALIAS_NOTE = (
    "Aliases opus, sonnet and haiku mean the newest version on the Anthropic API. "
    "Pin a full model ID in workspace agents/routing.json on Bedrock or Vertex."
)


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
    out = {"roles": roles, "notes": notes}
    jev = data.get("jev")
    if isinstance(jev, dict):
        out["jev"] = jev
    return out


def save_routing(workspace: Path, routing: dict) -> Path:
    path = routing_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "roles": routing.get("roles") or {},
        "notes": routing.get("notes") or {},
    }
    if "jev" in routing:
        payload["jev"] = routing["jev"]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _role_entry(routing: dict | None, role: str):
    if not routing:
        return None
    return routing.get("roles", {}).get(role)


def resolve_model(role: str, routing: dict | None, *, profile: str = "personal") -> str:
    """Model name for a role after defaults and workspace overrides."""
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    base = DEFAULT_MODELS[role]
    entry = _role_entry(routing, role)
    if isinstance(entry, dict) and isinstance(entry.get("model"), str) and entry["model"].strip():
        base = entry["model"].strip()
    elif isinstance(entry, str) and entry.strip():
        base = entry.strip()
    if role == "check" and base == "sonnet":
        return CHECK_MODEL_ALT
    return base


def resolve_effort(role: str, routing: dict | None, *, profile: str = "personal") -> str | None:
    """Effort level for a role, or None when the agent file should omit effort."""
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    base = DEFAULT_EFFORT.get(role)
    entry = _role_entry(routing, role)
    if isinstance(entry, dict) and isinstance(entry.get("effort"), str) and entry["effort"].strip():
        return entry["effort"].strip()
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


def parse_agent_effort(text: str) -> str | None:
    m = FRONTMATTER.match(text)
    if not m:
        return None
    found = EFFORT_LINE.search(m.group(1))
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


def set_agent_effort(text: str, effort: str | None) -> str:
    """Insert, replace or remove effort: in YAML frontmatter."""
    m = FRONTMATTER.match(text)
    if not m:
        return text
    body = m.group(1)
    if effort is None or not str(effort).strip():
        body = EFFORT_LINE.sub("", body)
        body = re.sub(r"\n{3,}", "\n\n", body)
    elif EFFORT_LINE.search(body):
        body = EFFORT_LINE.sub(f"effort: {effort}", body, count=1)
    else:
        body = body.rstrip() + f"\neffort: {effort}\n"
    return f"---\n{body}\n---\n{text[m.end():]}"


def routing_summary(routing: dict | None, profile: str) -> dict:
    """Resolved models and effort per role for CLI output."""
    routing = routing or {"roles": {}, "notes": {}}
    roles_out = {}
    for role in ROLES:
        roles_out[role] = {
            "model": resolve_model(role, routing, profile=profile),
            "effort": resolve_effort(role, routing, profile=profile),
        }
    return {
        "roles": roles_out,
        "defaults": dict(DEFAULT_MODELS),
        "default_effort": dict(DEFAULT_EFFORT),
        "jev": jev_config(routing, profile),
        "alias_note": ALIAS_NOTE,
        "provider_note": ALIAS_NOTE + " Claude Haiku 5.5 needs Claude Code >= v2.1.293.",
    }


def set_role_routing(routing: dict, role: str, model: str, effort: str | None = None) -> dict:
    """Update one role in a routing dict; effort None leaves the stored effort unchanged."""
    roles = dict(routing.get("roles") or {})
    entry = roles.get(role)
    if isinstance(entry, str):
        entry = {"model": entry.strip()}
    elif not isinstance(entry, dict):
        entry = {}
    entry = dict(entry)
    entry["model"] = model.strip()
    if effort is not None:
        if effort.strip():
            entry["effort"] = effort.strip()
        elif "effort" in entry:
            del entry["effort"]
    roles[role] = entry
    out = dict(routing)
    out["roles"] = roles
    return out
