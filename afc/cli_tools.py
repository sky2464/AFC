"""Tool commands: addons, tools.

Registered into the main parser by afc.cli through register().
"""

import argparse
import json
import shutil
from pathlib import Path

from afc import addons, tools

NAMES = ("addons", "tools")


def register(sub) -> None:
    p = sub.add_parser("addons", help="which account add-ons Flight Control sessions allow")
    p.set_defaults(handler=cmd_addons)
    t = sub.add_parser("tools", help="the project's skills and servers; 'tools add <name>' copies from the library")
    t.add_argument("words", nargs="*", help="add <name>")
    t.set_defaults(handler=cmd_tools)


def cmd_addons(args: argparse.Namespace) -> dict:
    from afc import cli  # late import: afc.cli imports this module

    root = cli.afc_root()
    try:
        ok = addons.allowed(root)
    except ValueError as exc:
        raise cli.CliError(str(exc))
    off, note = addons.blocked(root)
    out = {"allowed": ok, "blocked": off, "unknown_state": note is not None}
    if note:
        out["note"] = note
    return out


def _names(base: Path, skills: bool) -> list[str]:
    if not base.is_dir():
        return []
    if skills:
        return sorted(d.name for d in base.iterdir() if d.is_dir() and (d / "SKILL.md").is_file())
    return sorted(f.stem for f in base.glob("*.json"))


def _project_names(cli, ws: Path) -> dict:
    try:
        servers = sorted(tools.project_servers(ws))
    except tools.ToolsError as exc:
        raise cli.CliError(str(exc))
    return {"skills": _names(ws / "skills", True), "servers": servers}


def cmd_tools(args: argparse.Namespace) -> dict:
    from afc import cli  # late import: afc.cli imports this module

    words = args.words
    if words and (words[0] != "add" or len(words) != 2):
        raise cli.CliError("Use 'tools' to list, or 'tools add <name>' to add a library skill or server.")
    reg = cli.load_registry(cli.afc_home())
    ws = Path(cli._active(reg).workspace_path)
    lib = cli.afc_root() / "library"
    if not words:
        return {"project": _project_names(cli, ws),
                "library": {"skills": _names(lib / "skills", True), "servers": _names(lib / "mcp", False)}}
    return _add(cli, words[1], ws, lib)


def _add(cli, name: str, ws: Path, lib: Path) -> dict:
    if not tools._NAME.match(name):
        raise cli.CliError(f"'{name}' isn't a plain tool name.")
    have = _project_names(cli, ws)
    skill_src, recipe = lib / "skills" / name, lib / "mcp" / f"{name}.json"
    is_skill, is_server = (skill_src / "SKILL.md").is_file(), recipe.is_file()
    if not (is_skill or is_server):
        raise cli.CliError(f"The library has no skill or server named {name} - run 'tools' to see what it offers.")
    if (is_skill and name in have["skills"]) or (is_server and name in have["servers"]):
        raise cli.CliError(f"{name} is already in this project.")
    mcp = ws / "mcp.json"
    before = mcp.read_bytes() if mcp.exists() else None
    restore = tools.snapshot(cli.afc_root())
    try:
        if is_skill:
            shutil.copytree(skill_src, ws / "skills" / name)
        if is_server:
            _add_server(mcp, name, recipe)
        tools.swap_in(cli.afc_root(), ws)
    except (tools.ToolsError, OSError, ValueError) as exc:
        restore()
        if is_skill:
            shutil.rmtree(ws / "skills" / name, ignore_errors=True)
        if before is None:
            mcp.unlink(missing_ok=True)
        else:
            mcp.write_bytes(before)
        raise cli.CliError(str(exc))
    return {"added": name, "kind": [k for k, on in (("skill", is_skill), ("server", is_server)) if on],
            "note": "Tools load from the next start."}


def _add_server(mcp: Path, name: str, recipe: Path) -> None:
    entry = json.loads(recipe.read_text(encoding="utf-8"))
    if not isinstance(entry, dict):
        raise tools.ToolsError(f"{recipe} isn't a server recipe")
    entry = {k: v for k, v in entry.items() if k not in ("publisher", "vetted")}
    tools._entry(recipe, name, entry)  # refuses secrets and unexpected settings
    data = json.loads(mcp.read_text(encoding="utf-8")) if mcp.exists() else {"servers": {}}
    data.setdefault("servers", {})[name] = entry
    mcp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
