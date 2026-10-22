"""SessionStart hook: show the Flight Control banner and tell Claude about the active project.

Never fails: any problem reading the registry becomes a context line, and main returns 0.
"""

import json
import sys
from pathlib import Path

from afc.config import afc_home
from afc.registry import RegistryError, load_registry

BANNER = (
    "✈️  Flight Control — I build and manage your projects one small slice at a time, "
    "with security and architecture built in. Say hi to start — /afc is the only command you need."
)


def _context(home: Path) -> str:
    try:
        reg = load_registry(home)
    except RegistryError as exc:
        return f"Registry unreadable: {exc}. Tell the user and offer to repair it."
    active = reg.active()
    if active is None:
        project = "Active project: none — first run."
    else:
        project = (
            f"Active project: {active.name} ({active.profile}), code: {active.code_path}, "
            f"workspace: {active.workspace_path}, last slice: {active.last_slice or 'none'}."
        )
    others = [n for n in reg.projects if active is None or n != active.name]
    return (
        f"Flight Control session. {project} Other projects: {', '.join(others) or 'none'}. "
        "Follow CLAUDE.md and the afc-start skill for the first reply."
    )


def build_output(home: Path) -> dict:
    try:
        context = _context(home)
    except Exception as exc:  # the welcome must never break a session
        context = f"Registry unreadable: {exc}. Tell the user and offer to repair it."
    return {
        "systemMessage": BANNER,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context},
    }


def main(stdout=None) -> int:
    stdout = stdout or sys.stdout
    try:
        home = afc_home()
    except Exception:
        home = Path.home() / ".A-FC"
    stdout.write(json.dumps(build_output(home), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
