"""Install per-project role agents and routing at init (FC-022)."""

import json
import shutil
from pathlib import Path

from afc.config import afc_root
from afc.role_agents import (
    PROJECT_AGENT,
    ROUTING_NAME,
    ROLES,
    resolve_model,
    routing_path,
    set_agent_model,
)

TEMPLATE_AGENTS = afc_root() / "templates" / "project" / "agents"
TEMPLATE_WORKFLOW = afc_root() / "templates" / "project" / "workflows" / "afc-build-slice.js"
TEMPLATE_ROUTING = afc_root() / "templates" / "workspace" / "agents" / ROUTING_NAME


def ensure_routing(workspace: Path) -> Path:
    dest = routing_path(workspace)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() and TEMPLATE_ROUTING.is_file():
        shutil.copyfile(TEMPLATE_ROUTING, dest)
    elif not dest.exists():
        dest.write_text(
            json.dumps(
                {"roles": {}, "notes": {"main_session": "not_haiku"}, "jev": {"enabled": False, "mode": "off"}},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return dest


def install_code_agents(code: Path, workspace: Path, profile: str) -> dict:
    """Copy role agent templates into code/.claude/agents with resolved models."""
    routing_file = ensure_routing(workspace)
    routing = json.loads(routing_file.read_text(encoding="utf-8"))
    agents_dir = Path(code) / ".claude" / "agents"
    workflows_dir = Path(code) / ".claude" / "workflows"
    agents_dir.mkdir(parents=True, exist_ok=True)
    workflows_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for role in ROLES:
        name = PROJECT_AGENT[role]
        src = TEMPLATE_AGENTS / f"{name}.md"
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8")
        model = resolve_model(role, routing, profile=profile)
        dest = agents_dir / f"{name}.md"
        dest.write_text(set_agent_model(text, model), encoding="utf-8")
        written.append(name)
    wf_dest = workflows_dir / "afc-build-slice.js"
    if TEMPLATE_WORKFLOW.is_file() and not wf_dest.exists():
        shutil.copyfile(TEMPLATE_WORKFLOW, wf_dest)
    return {"agents_dir": str(agents_dir), "written": written, "routing": str(routing_file)}


def sync_project_agents(project) -> dict:
    """Re-materialize agents from templates and current routing."""
    return install_code_agents(
        Path(project.code_path), Path(project.workspace_path), project.profile or "personal"
    )
