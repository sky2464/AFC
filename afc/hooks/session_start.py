"""SessionStart hook: greet the user with the first question and tell Claude about the projects.

The welcome line already asks the first question with options 1 and 2, so the user can answer with
one key. The context line tells Claude what 1 and 2 mean.

Never fails: any problem reading the registry becomes a context line, and main returns 0.
"""

import json
import sys
from pathlib import Path

from afc.config import afc_home
from afc.registry import load_registry

INTRO = (
    "✈️  Flight Control — your AI architect, project manager and security officer in one.\n"
    "Spec-driven from day one: locks onto your goal, keeps every step on course, "
    "delivers a working app."
)
# Used when the projects can't be read: no options to offer, so a plain start.
BANNER = f"{INTRO}\nSay hi to start — /afc is the only command you need."
OR_HI = "or just say hi."
SLICE_CHARS = 40


def _short(text: str) -> str:
    return text if len(text) <= SLICE_CHARS else text[: SLICE_CHARS - 1].rstrip() + "…"


def _choices(reg) -> tuple[str, str, str]:
    """The welcome's question as (one, two, line): what 1 and 2 mean, and the line itself."""
    active = reg.active()
    if active is not None:
        last = f" (last: {_short(active.last_slice)})" if active.last_slice else ""
        one, two = f"continue {active.name}", "something else"
        return one, two, f"Welcome back. Type 1 to {one}{last}, 2 for {two}, {OR_HI}"
    if reg.ready():
        one, two = "pick one of your projects", "start a new project"
        return one, two, f"Welcome back. Type 1 to {one}, 2 to {two}, {OR_HI}"
    if reg.paused():
        one, two = "resume a paused project", "start a new project"
        return one, two, f"Welcome back. Type 1 to {one}, 2 to {two}, {OR_HI}"
    one, two = "start a new project", "bring in one already on this computer"
    return one, two, f"Type 1 to {one}, 2 to {two}, {OR_HI}"


def _project_line(reg) -> str:
    active = reg.active()
    if active is None:
        project = "Active project: none — first run." if not reg.projects else "Active project: none."
    else:
        project = (
            f"Active project: {active.name} ({active.profile}), code: {active.code_path}, "
            f"workspace: {active.workspace_path}, last slice: {active.last_slice or 'none'}."
        )
    others = [n for n in reg.ready() if active is None or n != active.name]
    paused = f" Paused: {', '.join(reg.paused())}." if reg.paused() else ""
    return f"{project} Other projects: {', '.join(others) or 'none'}.{paused}"


def _health_line(home: Path) -> str:
    """A short note when the health check finds problems, so Claude can mention them."""
    try:
        from afc.cli_health import find_problems

        count = len(find_problems(home))
    except Exception:  # the welcome must never break over a health check
        return ""
    if not count:
        return ""
    noun = "problem" if count == 1 else "problems"
    return (f" Health check: {count} {noun} (sh bin/afc check). After answering the first message, "
            "mention it in one line and offer to look.")


def build_output(home: Path) -> dict:
    try:
        reg = load_registry(home)
        one, two, line = _choices(reg)
        message = f"{INTRO}\n{line}"
        context = (
            f"Flight Control session. {_project_line(reg)} The welcome asked: 1 = {one}, "
            f"2 = {two}.{_health_line(home)} Follow CLAUDE.md and the afc-start skill for the "
            "first reply."
        )
    except Exception as exc:  # a RegistryError or anything else: the welcome must never break
        message = BANNER
        context = f"Registry unreadable: {exc}. Tell the user and offer to repair it."
    return {
        "systemMessage": message,
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
