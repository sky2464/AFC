"""Path rule: writes (direct or via Bash) must stay inside the active project."""

from afc.hooks.common import (
    WRITE_TOOLS,
    Context,
    GuardInputError,
    bash_write_targets,
    check_paths_reason,
    target_path,
)
from pathlib import Path


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
        cwd = event.get("cwd") or "/"
        targets = [_bash_target(raw, cwd) for raw in bash_write_targets(command)]
    else:
        return None
    for path in targets:
        reason = check_paths_reason(path, ctx)
        if reason:
            return reason
    return None


def _bash_target(raw: str, cwd: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(cwd) / path
    return path.resolve()
