"""`afc model` — which tool/model is shown, and which to pick (FC-052)."""

from __future__ import annotations

import argparse
from pathlib import Path

from afc.tool_model import (
    HEAVY_ROLES,
    detect_tool,
    fit,
    heavy_job_asked,
    mark_heavy_job_asked,
    need,
    role_switch_suggest,
    session_suggest,
    shown_model,
    suggest,
    three_options,
)

NAMES = ("model",)


def register(sub) -> None:
    p = sub.add_parser("model", help="which AI tool and model to use")
    p.add_argument("--tool", choices=("claude", "cursor", "codex", "copilot", "antigravity"))
    p.add_argument("--role", help="FC-050 role (architect, builder, …) for a switch tip")
    p.add_argument(
        "--options",
        action="store_true",
        help="three options (premium / best cost / hybrid) from local + look-up",
    )
    p.set_defaults(handler=cmd_model)
    psub = p.add_subparsers(dest="model_cmd")
    choose = psub.add_parser("choose", help="keep a model choice for this tool in the project")
    choose.add_argument("model")
    choose.add_argument("--tool", choices=("claude", "cursor", "codex", "copilot", "antigravity"))
    choose.set_defaults(handler=cmd_choose)


def _active():
    from afc.cli import NO_ACTIVE, CliError
    from afc.config import afc_home
    from afc.registry import load_registry

    project = load_registry(afc_home()).active()
    if project is None:
        raise CliError(NO_ACTIVE)
    return project


def _routing_and_profile(project=None):
    """Active project's routing and profile when one is set; else empty routing."""
    from afc.role_agents import load_routing

    if project is None:
        try:
            project = _active()
        except Exception:
            return {}, "personal", None
    return (
        load_routing(Path(project.workspace_path)),
        project.profile or "personal",
        project,
    )


def _ask_payload(tool: str, shown: dict, routing: dict, profile: str) -> dict:
    """Build ask / kept / options / suggest for a non-Claude tool."""
    from afc.role_agents import tool_kept

    current = shown.get("model")
    kept = tool_kept(routing, tool)
    out: dict = {
        "tool": tool,
        "model": current,
        "file": shown.get("file"),
        "shown": shown.get("shown", False),
        "detail": shown.get("detail", "not shown"),
    }
    if kept:
        out["kept"] = kept["model"]
        out["seen"] = kept.get("seen")

    # Ask again only when nothing is kept, or the tool's shown model changed since the choice.
    if kept and kept.get("seen") == (current or None):
        out["ask"] = False
        return out

    out["ask"] = True
    if current:
        tip = session_suggest(routing, shown=shown, profile=profile)
        if tip:
            out["suggest"] = tip
    else:
        result = three_options(tool)
        out["options"] = result["options"]
        out["recommended"] = result["recommended"]
        if result.get("note"):
            out["note"] = result["note"]
    return out


def cmd_model(args: argparse.Namespace) -> dict:
    tool = getattr(args, "tool", None) or detect_tool()
    role = getattr(args, "role", None)
    want_options = bool(getattr(args, "options", False))

    if want_options:
        result = three_options(tool)
        out = {
            "tool": result["tool"],
            "options": result["options"],
            "recommended": result["recommended"],
        }
        if result.get("note"):
            out["note"] = result["note"]
        lookup = result.get("lookup") or {}
        if lookup.get("checked"):
            out["checked"] = lookup["checked"]
        if lookup.get("source"):
            out["source"] = lookup["source"]
        return out

    shown = shown_model(tool)
    routing, profile, _project = _routing_and_profile()

    # Claude Code: FC-050 routing; never the other-tools ask (A7).
    if tool == "claude":
        out = {
            "tool": "claude",
            "model": shown.get("model"),
            "file": shown.get("file"),
            "shown": shown.get("shown", False),
            "detail": shown.get("detail", "not shown"),
            "ask": False,
            "agents": "sh bin/afc agents",
        }
        if role:
            tip = suggest(role, routing, shown=shown, profile=profile)
            if tip:
                out["suggest"] = tip
        return out

    if role:
        from afc.config import afc_home
        from afc.role_agents import tool_kept

        out = {
            "tool": shown.get("tool") or tool,
            "model": shown.get("model"),
            "file": shown.get("file"),
            "shown": shown.get("shown", False),
            "detail": shown.get("detail", "not shown"),
        }
        kept = tool_kept(routing, tool)
        if kept:
            out["kept"] = kept["model"]
        home = afc_home()
        if role in HEAVY_ROLES:
            tip = role_switch_suggest(role, routing, shown=shown, profile=profile, home=home)
            if tip:
                out["suggest"] = tip
            light_kept = kept and fit(kept["model"]) == "light"
            strong_job = need(role, routing, profile=profile) == "strong"
            ask = bool(tip and light_kept and strong_job and not heavy_job_asked(home, tool))
            out["ask"] = ask
            if ask:
                mark_heavy_job_asked(home, tool)
        else:
            tip = suggest(role, routing, shown=shown, profile=profile)
            if tip:
                out["suggest"] = tip
            out["ask"] = False
        return out

    return _ask_payload(tool, shown, routing, profile)


def cmd_choose(args: argparse.Namespace) -> dict:
    from afc.cli import CliError
    from afc.role_agents import load_routing, save_routing, set_tool_choice

    project = _active()
    tool = getattr(args, "tool", None) or detect_tool()
    if tool in ("claude", "unknown"):
        raise CliError(
            "model choose is for Cursor, Codex, Copilot or Antigravity — "
            "in Claude Code use sh bin/afc agents"
        )
    shown = shown_model(tool)
    ws = Path(project.workspace_path)
    routing = load_routing(ws)
    try:
        updated = set_tool_choice(routing, tool, args.model, shown.get("model"))
    except ValueError as exc:
        raise CliError(str(exc)) from exc
    save_routing(ws, updated)
    kept = updated["tools"][tool]
    return {
        "tool": tool,
        "kept": kept.get("model"),
        "seen": kept.get("seen"),
        "file": str(ws / "agents" / "routing.json"),
        "ask": False,
    }
