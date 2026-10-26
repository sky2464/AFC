"""Path rule: writes (direct or via Bash) must stay inside the active project."""

import re
import shlex
from pathlib import Path

from afc.hooks.common import (
    WRITE_TOOLS,
    Context,
    GuardInputError,
    UNREADABLE_REASON,
    bash_write_targets_or_none,
    check_paths_reason,
    resolve_path,
    string_values,
    target_path,
)
from afc.registry import RegistryError, load_registry

FOREIGN_REASON = ("this is a test copy and works only in its own test workspace; "
                  "the real Flight Control workspace and its projects are off limits here")
READ_TOOLS = ("Read", "Glob", "Grep", "LS")
_PATH_KEYS = ("file_path", "path", "notebook_path")


def foreign_roots(ctx: Context) -> list[Path]:
    """In a test-home session, the real ~/.A-FC and the code folders of projects registered only
    there. Empty in a normal session. Never raises."""
    try:
        real = (Path.home() / ".A-FC").resolve()
        if ctx.home.resolve() == real:
            return []
        roots = [real]
        try:
            ours = {resolve_path(p.code_path) for p in ctx.projects}
            theirs = load_registry(real).projects.values()
        except (RegistryError, OSError):
            return roots
        roots += [r for r in (resolve_path(p.code_path) for p in theirs) if r not in ours]
        return roots
    except (OSError, RuntimeError):
        return []


def _spellings(root: Path) -> list[str]:
    forms = [str(root)]
    try:
        rel = root.relative_to(Path.home().resolve())
        forms += [f"~/{rel}", f"$HOME/{rel}", f"${{HOME}}/{rel}"]
    except ValueError:
        pass
    return forms


def _command_tokens(command: str) -> list[str]:
    """Words of a shell command, also split at ; & | < > = and parentheses, so a relative
    spelling like `ls ../.A-FC` or `cat x>../.A-FC/f` is seen."""
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        words = command.split()
    out: list[str] = []
    for w in words:
        out.append(w)
        out += [t for t in re.split(r"[;&|<>=()]+", w) if t and t != w]
    return out


def check_foreign_home(event: dict, ctx: Context) -> str | None:
    """Block any tool call that names the real workspace (or a project registered only there)
    while the session's workspace is a test home. Reads included."""
    roots = foreign_roots(ctx)
    if not roots:
        return None
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    cwd = event.get("cwd")
    for key in _PATH_KEYS:
        raw = tool_input.get(key)
        if isinstance(raw, str) and raw:
            path = resolve_path(raw, cwd)
            if any(path == r or path.is_relative_to(r) for r in roots):
                return FOREIGN_REASON
    command = tool_input.get("command")
    if event.get("tool_name") == "Bash" and isinstance(command, str):
        for token in _command_tokens(command):
            if token in (".", "..") or "/" in token:
                path = resolve_path(token, cwd)
                if any(path == r or path.is_relative_to(r) for r in roots):
                    return FOREIGN_REASON
    for text in string_values(tool_input):
        for root in roots:
            for form in _spellings(root):
                if re.search(re.escape(form) + r"(?![\w.-])", text):
                    return FOREIGN_REASON
    return None


def check_paths(event: dict, ctx: Context) -> str | None:
    """Return a block reason when the event writes outside the allowed roots, else None."""
    tool = event.get("tool_name")
    if tool in WRITE_TOOLS:
        target = target_path(event)
        if target is None:
            raise GuardInputError(f"{tool} event has no file path; cannot check it")
        targets = [target]
    elif tool == "Bash":
        tool_input = event.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str):
            return None
        found = bash_write_targets_or_none(command, event.get("cwd") or "/")
        if found is None:
            return UNREADABLE_REASON
        targets = [Path(t) for t in found]
    else:
        return None
    for path in targets:
        reason = check_paths_reason(path, ctx)
        if reason:
            return reason
    return None
