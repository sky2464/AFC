"""Path rule: writes (direct or via Bash) must stay inside the active project."""

from pathlib import Path

from afc.hooks.common import (
    WRITE_TOOLS,
    Context,
    GuardInputError,
    UNREADABLE_REASON,
    bash_write_targets_or_none,
    check_paths_reason,
    target_path,
)


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
