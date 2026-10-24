"""Maintenance rule: while Flight Control itself is being worked on, no project is touched.

In maintenance mode, writes into any registered project's code or workspace folder, and git
commands that run in or point at those folders, are blocked. Reading stays allowed. Outside
maintenance mode this rule does nothing.
"""

from pathlib import Path

from afc.hooks.common import (
    WRITE_TOOLS,
    Context,
    bash_write_targets_or_none,
    resolve_path,
    target_path,
)
from afc.hooks.rules_git import parse_git, simple_commands

_LOCATION_OPTS = {"-C", "--git-dir", "--work-tree"}
_VALUE_OPTS = {*_LOCATION_OPTS, "-c", "--namespace", "--config-env"}


def _project_folders(ctx: Context) -> list[tuple[str, Path]]:
    """(project name, folder) for every project's code and workspace folder.

    A folder that is, or holds, Flight Control or its workspace home is skipped: blocking it
    would block maintenance itself (the registry should never hold one; remove and relocate
    refuse them).
    """
    keep = [ctx.root.resolve(), ctx.home.resolve()]
    folders: list[tuple[str, Path]] = []
    for project in ctx.projects:
        for raw in (project.code_path, project.workspace_path):
            folder = resolve_path(raw)
            if not any(k == folder or k.is_relative_to(folder) for k in keep):
                folders.append((project.name, folder))
    return folders


def _owner(path: Path, folders: list[tuple[str, Path]]) -> str | None:
    for name, folder in folders:
        if path == folder or path.is_relative_to(folder):
            return name
    return None


def _git_locations(words: list[str], base: Path) -> list[Path]:
    """Folders a git command works in: where it runs, plus -C, --git-dir and --work-tree.

    Git applies -C first, so later options are relative to the folder -C moved to.
    """
    found = [base]
    here = base
    i = 1
    while i < len(words) and words[i].startswith("-"):
        key, eq, inline = words[i].partition("=")
        takes_value = not eq and key in _VALUE_OPTS
        value = inline if eq else (words[i + 1] if takes_value and i + 1 < len(words) else "")
        if value and key in _LOCATION_OPTS:
            place = resolve_path(value, str(here))
            if key == "-C":
                here = place
            found.append(place)
        i += 2 if takes_value else 1
    return found


def check_maintenance(event: dict, ctx: Context) -> str | None:
    """Return a block reason when maintenance mode would reach into a project, else None."""
    if not ctx.maintain:
        return None
    folders = _project_folders(ctx)
    if not folders:
        return None
    tool = event.get("tool_name")
    if tool in WRITE_TOOLS:
        target = target_path(event)
        owner = _owner(target, folders) if target is not None else None
        return _write_reason(target, owner) if owner else None
    if tool != "Bash":
        return None
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return None
    cwd = event.get("cwd") or "/"
    for raw in bash_write_targets_or_none(command, cwd) or []:
        owner = _owner(Path(raw), folders)
        if owner:
            return _write_reason(Path(raw), owner)
    for words, base in simple_commands(command, cwd) or []:
        if parse_git(words) is None:
            continue
        for where in _git_locations(words, base):
            owner = _owner(where, folders)
            if owner:
                return (f"maintenance mode is on, so git can't run in {where} (project {owner}) "
                        "— project work needs maintenance mode off")
    return None


def _write_reason(path: Path, owner: str) -> str:
    return (f"maintenance mode is on, so {path} (project {owner}) is off limits "
            "— project work needs maintenance mode off")
