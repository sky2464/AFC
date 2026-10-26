"""Role agent routing commands."""

import argparse
from pathlib import Path

from afc.config import afc_home
from afc.project_agents import sync_project_agents, write_role_agent
from afc.registry import load_registry
from afc.role_agents import (
    ROLES,
    load_routing,
    routing_path,
    routing_summary,
    save_routing,
    set_role_routing,
)

NAMES = ("agents",)


def register(sub) -> None:
    p = sub.add_parser("agents", help="show or sync per-role models and agents")
    p.set_defaults(handler=cmd_show)
    psub = p.add_subparsers(dest="agents_cmd")
    sync = psub.add_parser("sync", help="rewrite .claude/agents from templates and routing")
    sync.set_defaults(handler=cmd_sync)
    setp = psub.add_parser("set", help="set one role model (and optional effort) in routing")
    setp.add_argument("role", choices=ROLES)
    setp.add_argument("model")
    setp.add_argument("--effort", help="low, medium, high, max (role default when omitted)")
    setp.set_defaults(handler=cmd_set)


def _active():
    from afc.cli import NO_ACTIVE, CliError

    reg = load_registry(afc_home())
    project = reg.active()
    if project is None:
        raise CliError(NO_ACTIVE)
    return project


def cmd_show(args: argparse.Namespace) -> dict:
    project = _active()
    ws = Path(project.workspace_path)
    routing = load_routing(ws)
    summary = routing_summary(routing, project.profile or "personal")
    summary["routing_file"] = str(routing_path(ws))
    summary["code_agents"] = str(Path(project.code_path) / ".claude" / "agents")
    return summary


def cmd_sync(args: argparse.Namespace) -> dict:
    project = _active()
    return sync_project_agents(project)


def cmd_set(args: argparse.Namespace) -> dict:
    project = _active()
    ws = Path(project.workspace_path)
    routing = load_routing(ws)
    effort_arg = args.effort
    updated = set_role_routing(routing, args.role, args.model, effort_arg)
    save_routing(ws, updated)
    name = write_role_agent(
        Path(project.code_path), ws, project.profile or "personal", args.role
    )
    resolved = routing_summary(updated, project.profile or "personal")["roles"][args.role]
    return {
        "role": args.role,
        "agent": name,
        "model": resolved["model"],
        "effort": resolved["effort"],
        "routing_file": str(routing_path(ws)),
    }
