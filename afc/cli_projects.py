"""Project lifecycle commands: pause, resume and remove.

Registered into the main parser by afc.cli through register(). Pausing parks a project
without touching its folders. Removing never deletes: folders move to
~/.A-FC/removed/<name>-<date>/, where the user can get them back or delete them.
"""

import argparse
import shutil
from datetime import date
from pathlib import Path

from afc.config import afc_home
from afc.registry import PAUSED, Project, load_registry, save_registry
from afc import tools
from afc.session_dirs import grant_dirs

NAMES = ("pause", "resume", "remove")


def register(sub) -> None:
    p = sub.add_parser("pause", help="park a project; it stops being offered until resumed")
    p.add_argument("name")
    p.set_defaults(handler=cmd_pause)

    p = sub.add_parser("resume", help="bring a paused project back and make it active")
    p.add_argument("name")
    p.set_defaults(handler=cmd_resume)

    p = sub.add_parser("remove", help="take a project off the list and put its folders away")
    p.add_argument("name")
    p.add_argument("--code", action="store_true", help="also put the code folder away")
    p.set_defaults(handler=cmd_remove)


def _cli():
    from afc import cli  # late import: afc.cli imports this module

    return cli


def cmd_pause(args: argparse.Namespace) -> dict:
    """Mark the project paused. If it was active, no project is active and its folder grants
    are cleared; its folders are left exactly where they are."""
    cli = _cli()
    home = afc_home()
    reg = load_registry(home)
    project = _known(reg, args.name)
    if project.status == PAUSED:
        raise cli.CliError(f"{project.name} is already paused.")
    was_active = reg.active_name == project.name
    reg.update(project.name, status=PAUSED)
    if was_active:
        reg.active_name = None
    undo = cli._settings_undo()
    try:
        if was_active:
            undo.save_settings()
            undo.on_rollback(tools.snapshot(cli.afc_root()))
            grant_dirs(cli.afc_root(), [])
            tools.clear(cli.afc_root())
        save_registry(home, reg)
    except BaseException:
        undo.rollback()
        raise
    return {"paused": project.name, "was_active": was_active}


def cmd_resume(args: argparse.Namespace) -> dict:
    """Unpause the project and make it the active one, like switch."""
    cli = _cli()
    home = afc_home()
    reg = load_registry(home)
    project = _known(reg, args.name)
    if project.status != PAUSED:
        raise cli.CliError(f"{project.name} isn't paused.")
    reg.update(project.name, status="active", last_active=cli._today())
    reg.set_active(project.name)
    undo = cli._settings_undo()
    try:
        granted = cli._commit(home, reg, project, undo)
    except BaseException:
        undo.rollback()
        raise
    return {"resumed": project.name, **cli._project_result(project, granted)}


def _known(reg, name: str) -> Project:
    project = reg.get(name)
    if project is None:
        cli = _cli()
        raise cli.CliError(cli._unknown_name(name))
    return project


def cmd_remove(args: argparse.Namespace) -> dict:
    """The workspace always moves; the code folder moves only with --code. If anything fails,
    the folders move back and the list and settings stay as they were."""
    cli = _cli()
    home = afc_home()
    reg = load_registry(home)
    project = _known(reg, args.name)
    was_active = reg.active_name == project.name
    moves = [("workspace", _owned_workspace(home, project))]
    if args.code:
        moves.append(("code", _removable_code(home, project)))
    dest = _removed_dir(home, project.name)
    undo = cli._settings_undo()
    done: list[tuple[str, Path, Path]] = []
    try:
        for label, src in moves:
            if src is not None and src.exists():
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest / label))
                done.append((label, src, dest / label))
        reg.remove(project.name)
        if was_active:
            undo.save_settings()
            undo.on_rollback(tools.snapshot(cli.afc_root()))
            grant_dirs(cli.afc_root(), [])
            tools.clear(cli.afc_root())
        save_registry(home, reg)
    except BaseException:
        undo.rollback()
        for _, src, moved in reversed(done):
            shutil.move(str(moved), str(src))
        if dest.exists() and not any(dest.iterdir()):
            dest.rmdir()
        raise
    result: dict = {
        "removed": project.name,
        "was_active": was_active,
        "moved": {label: str(moved) for label, _, moved in done},
    }
    if not args.code:
        result["code_left_at"] = project.code_path
    return result


def _owned_workspace(home: Path, project: Project) -> Path | None:
    """The workspace, only when it sits in Flight Control's own projects folder."""
    workspace = Path(project.workspace_path).resolve()
    return workspace if workspace.is_relative_to((home / "projects").resolve()) else None


def _removable_code(home: Path, project: Project) -> Path:
    """The code folder, refused when moving it would take something bigger with it."""
    cli = _cli()
    code = Path(project.code_path).resolve()
    protected = [Path.home().resolve(), home.resolve(), cli.afc_root().resolve()]
    if code == Path(code.anchor) or any(p == code or p.is_relative_to(code) for p in protected):
        raise cli.CliError(f"Won't move {code}: it holds more than this project.")
    return code


def _removed_dir(home: Path, name: str) -> Path:
    base = home / "removed" / f"{name}-{date.today():%Y%m%d}"
    dest, n = base, 2
    while dest.exists():
        dest, n = base.with_name(f"{base.name}-{n}"), n + 1
    return dest
