"""Company-resource rule: text or files from a workspace's resources/ must not reach a repo.

Writes inside the Flight Control workspace are always allowed; summaries belong there.
"""

from pathlib import Path

from afc.fingerprint import leaks, load_fingerprints
from afc.hooks.common import (
    CANT_FOLLOW,
    UNREADABLE_REASON,
    WRITE_TOOLS,
    Context,
    cd_base,
    expand_vars,
    lex,
    resolve_path,
    shell_script,
    split_commands,
    strip_prefix,
    string_values,
    target_path,
)

TEXT_REASON = ("this contains company resource text — keep it in the project workspace "
               "and write your own summary in the repo instead")
FILE_REASON = "this copies a company resource file out of the workspace — keep it in the workspace"
_COPY = {"cp", "mv", "rsync"}


def _within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def active_fingerprints(ctx: Context) -> set[str]:
    """Fingerprints of the active project's resources; empty without one."""
    if ctx.active is None:
        return set()
    return load_fingerprints(Path(ctx.active.workspace_path))


def _is_resource(path: Path, home: Path) -> bool:
    """Under <home>/projects/<name>/resources (or is that folder, or contains it)."""
    projects = home / "projects"
    if not _within(path, projects) and not _within(projects, path):
        return False
    if _within(projects, path):
        return True  # copying projects/ or a parent of it carries resources along
    parts = path.relative_to(projects).parts
    return len(parts) < 2 or parts[1] == "resources"


def _copy_paths(args: list[str]) -> tuple[list[str], list[str]]:
    """(sources, destinations) of cp/mv/rsync arguments."""
    dest = None
    positional = []
    skip = False
    for i, arg in enumerate(args):
        if skip:
            skip = False
            continue
        if arg in ("-t", "--target-directory"):
            dest, skip = (args[i + 1] if i + 1 < len(args) else None), True
        elif arg.startswith("--target-directory="):
            dest = arg.split("=", 1)[1]
        elif arg.startswith("-"):
            continue
        else:
            positional.append(arg)
    if dest is not None:
        return positional, [dest]
    if len(positional) < 2:
        return [], []
    return positional[:-1], positional[-1:]


def _bash_reason(command: str, cwd: str, home: Path, depth: int = 0) -> str | None:
    tokens = lex(command)
    if tokens is None:
        return UNREADABLE_REASON
    base = resolve_path(cwd)
    for words, _ in split_commands(tokens):
        words = strip_prefix(words)
        if not words:
            continue
        name = Path(words[0]).name
        if name == "cd":
            base = cd_base(words[1:], base)
        elif (script := shell_script(words, base, depth)) is not None:
            if script is CANT_FOLLOW:
                return UNREADABLE_REASON
            reason = _bash_reason(script, str(base), home, depth + 1)
            if reason:
                return reason
        elif name in _COPY:
            sources, dests = _copy_paths(words[1:])
            src = [expand_vars(s) for s in sources]
            dst = [expand_vars(d) for d in dests]
            if any(s is None for s in src) or any(d is None for d in dst):
                if any("resources" in s for s in sources):
                    return UNREADABLE_REASON
                continue
            if not any(_is_resource(resolve_path(s, str(base)), home) for s in src):
                continue
            if any(not _within(resolve_path(d, str(base)), home) for d in dst):
                return FILE_REASON
    return None


def check_resources(event: dict, ctx: Context) -> str | None:
    """Reason to block a write or copy that would carry company resources out, or None."""
    tool = event.get("tool_name")
    home = resolve_path(str(ctx.home))
    if tool in WRITE_TOOLS:
        path = target_path(event)
        if path is None or _within(path, home):
            return None
        fps = active_fingerprints(ctx)
        if any(leaks(s, fps) for s in string_values(event.get("tool_input"))):
            return TEXT_REASON
        return None
    if tool == "Bash":
        tool_input = event.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str) or not command:
            return None
        return _bash_reason(command, event.get("cwd") or "/", home)
    return None
