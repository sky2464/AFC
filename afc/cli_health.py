"""Health commands: check, repair and relocate.

Registered into the main parser by afc.cli through register(). check only reads; repair fixes
what needs no decision (folder access, missing or leftover workspaces); relocate points a project
at its code folder after the user moved it. Nothing is ever deleted.
"""

import argparse
import shutil
from pathlib import Path

from afc.config import afc_home
from afc.registry import load_registry, save_registry
from afc.session_dirs import GrantError, drop_dirs, grant_dirs, granted_now
from afc.workspace import create_workspace

NAMES = ("check", "repair", "relocate")
ACCESS = ("stale_access", "gone_access", "missing_access")


def register(sub) -> None:
    p = sub.add_parser("check", help="find problems across all projects (changes nothing)")
    p.set_defaults(handler=cmd_check)

    p = sub.add_parser("repair", help="fix the problems that need no decision")
    p.set_defaults(handler=cmd_repair)

    p = sub.add_parser("relocate", help="point a project at its code folder's new place")
    p.add_argument("name")
    p.add_argument("--path", required=True)
    p.set_defaults(handler=cmd_relocate)


def _cli():
    from afc import cli  # late import: afc.cli imports this module

    return cli


def cmd_check(args: argparse.Namespace) -> dict:
    problems = find_problems(afc_home())
    return {"ok": not problems, "problems": problems}


def cmd_repair(args: argparse.Namespace) -> dict:
    """Recreate missing workspaces, put leftover ones away, and set folder access to exactly the
    active project's folders, dropping entries for folders that no longer exist."""
    cli = _cli()
    home = afc_home()
    reg = load_registry(home)
    repaired: list[str] = []
    for p in find_problems(home):
        if p["kind"] == "workspace_missing" and p["fixable"]:
            create_workspace(home, p["project"])
            repaired.append(f"Recreated the empty workspace for {p['project']}.")
        elif p["kind"] == "orphan_workspace":
            from afc.cli_projects import _removed_dir

            dest = _removed_dir(home, Path(p["path"]).name)
            dest.mkdir(parents=True)
            shutil.move(p["path"], str(dest / "workspace"))
            repaired.append(f"Put the leftover workspace {p['path']} away in {dest}.")
    access = [p for p in find_problems(home) if p["kind"] in ACCESS]
    if access:
        undo = cli._settings_undo()
        undo.save_settings()
        try:
            grant_dirs(cli.afc_root(), _wanted(reg))
            drop_dirs(cli.afc_root(), [p["path"] for p in access if p["kind"] == "gone_access"])
        except BaseException:
            undo.rollback()
            raise
        repaired.append("Folder access now matches the active project.")
    return {"repaired": repaired, "left": find_problems(home)}


def cmd_relocate(args: argparse.Namespace) -> dict:
    cli = _cli()
    home = afc_home()
    reg = load_registry(home)
    project = reg.get(args.name)
    if project is None:
        raise cli.CliError(cli._unknown_name(args.name))
    new = Path(args.path).expanduser().resolve()
    if not new.is_dir():
        raise cli.CliError(f"Folder {new} does not exist.")
    protected = [Path.home().resolve(), home.resolve(), cli.afc_root().resolve()]
    if new == Path(new.anchor) or any(p == new or p.is_relative_to(new) for p in protected):
        raise cli.CliError(f"{new} holds more than one project's code. Pick the app's own folder.")
    for other in reg.projects.values():
        if other.name != project.name and Path(other.code_path).resolve() == new:
            raise cli.CliError(f"{new} is already the code folder of {other.name}.")
    reg.update(project.name, code_path=str(new))
    if reg.active_name == project.name:
        undo = cli._settings_undo()
        try:
            cli._commit(home, reg, project, undo)
        except BaseException:
            undo.rollback()
            raise
    else:
        save_registry(home, reg)
    return {"relocated": project.name, "code_path": str(new)}


def find_problems(home: Path) -> list[dict]:
    """Every problem as {kind, project?, path, detail, fixable}. Reads only."""
    cli = _cli()
    reg = load_registry(home)
    problems: list[dict] = []
    owned: set[Path] = set()
    for p in reg.projects.values():
        owned.add(Path(p.workspace_path).resolve())
        if not Path(p.code_path).is_dir():
            problems.append(_problem(
                "code_missing", p.code_path, False, project=p.name,
                detail=f"{p.name}: its code folder is gone from {p.code_path}. If it moved, "
                       "relocate it; if it's no longer wanted, remove the project."))
        if not Path(p.workspace_path).is_dir():
            ours = Path(p.workspace_path).resolve() == (home / "projects" / p.name).resolve()
            problems.append(_problem(
                "workspace_missing", p.workspace_path, ours, project=p.name,
                detail=f"{p.name}: its Flight Control workspace is missing; "
                       + ("repair recreates an empty one." if ours else "it lives outside ~/.A-FC.")))
    projects_dir = home / "projects"
    if projects_dir.is_dir():
        for d in sorted(projects_dir.iterdir()):
            if d.is_dir() and d.resolve() not in owned:
                problems.append(_problem(
                    "orphan_workspace", str(d), True,
                    detail=f"{d.name}: a leftover workspace that belongs to no project."))
    try:
        current, ours = granted_now(cli.afc_root())
    except GrantError as exc:
        problems.append(_problem("settings_unreadable", "", False, detail=str(exc)))
        return problems
    wanted = _wanted(reg)
    for entry in current:
        if not Path(entry).exists():
            problems.append(_problem("gone_access", entry, True,
                                     detail=f"Claude still has access to {entry}, which no longer exists."))
        elif entry in ours and entry not in wanted:
            problems.append(_problem("stale_access", entry, True,
                                     detail=f"Claude still has access to {entry}, which isn't the active project."))
    for entry in wanted:
        if entry not in current:
            problems.append(_problem("missing_access", entry, True,
                                     detail=f"The active project's folder {entry} isn't open to Claude."))
    return problems


def _wanted(reg) -> list[str]:
    """The active project's folders that exist: what folder access should be."""
    active = reg.active()
    if active is None:
        return []
    dirs = [Path(active.code_path), Path(active.workspace_path)]
    return [str(d.resolve()) for d in dirs if d.is_dir()]


def _problem(kind: str, path: str, fixable: bool, detail: str, project: str = "") -> dict:
    found = {"kind": kind, "path": path, "detail": detail, "fixable": fixable}
    if project:
        found["project"] = project
    return found
