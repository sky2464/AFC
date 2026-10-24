"""SessionStart hook: greet the user with the first question and tell Claude about the projects.

The welcome line already asks the first question with options 1 and 2, so the user can answer with
one key. The context line tells Claude what 1 and 2 mean.

Never fails: any problem reading the registry becomes a context line, and main returns 0.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from afc.config import afc_home, afc_root, maintain_enabled, valid_session
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


def _spec_note(active) -> str:
    try:
        from afc.plan import now_line

        return now_line(Path(active.workspace_path))
    except Exception:  # the welcome must never break
        return ""


def _project_line(reg) -> str:
    active = reg.active()
    if active is None:
        project = "Active project: none — first run." if not reg.projects else "Active project: none."
    else:
        project = (
            f"Active project: {active.name} ({active.profile}), code: {active.code_path}, "
            f"workspace: {active.workspace_path}, last slice: {active.last_slice or 'none'}."
        )
    spec = _spec_note(active) if active is not None else ""
    project += f" Active spec: {spec}." if spec else ""
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


def _branch(root: Path) -> str:
    """The Flight Control folder's git branch, or 'unknown'. Never raises."""
    try:
        done = subprocess.run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                              capture_output=True, text=True, timeout=3)
        name = done.stdout.strip()
        if done.returncode != 0 or not name:
            return "unknown"
        return "detached" if name == "HEAD" else name
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _maintenance_output() -> dict:
    """The welcome for a maintenance session: Flight Control itself, no projects offered."""
    root = afc_root()
    branch = _branch(root)
    message = (
        f"{INTRO}\n🔧 Maintenance: working on Flight Control itself · {root.name} · {branch}\n"
        "Projects are set aside. Type /afc mm off to go back to them."
    )
    context = (
        f"Flight Control session. Mode: maintenance — working on Flight Control itself in {root} "
        f"on branch {branch}. Plan: docs/master-plan.md. Projects are set aside: do not read, "
        "build or change any project, and ignore the active project. For the first reply, follow "
        "the maintenance case of the afc-start skill."
    )
    return _wrap(message, context)


def _wrap(message: str, context: str) -> dict:
    return {
        "systemMessage": message,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context},
    }


def build_output(home: Path, session: str | None = None) -> dict:
    if maintain_enabled(home, session):
        try:
            return _maintenance_output()
        except Exception:  # the welcome must never break
            pass
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
    return _wrap(message, context)


def _with_home_note(out: dict, home: Path) -> dict:
    """Tell Claude when the workspace isn't ~/.A-FC. Only test copies set one, so the welcome itself
    stays clean; Claude can mention it when it matters."""
    try:
        if home == (Path.home() / ".A-FC").resolve():
            return out
    except Exception:  # the welcome must never break
        return out
    context = out["hookSpecificOutput"]["additionalContext"]
    out["hookSpecificOutput"]["additionalContext"] = (
        f"{context} The workspace is a test home {home}, not ~/.A-FC.")
    return out


def _session_in(stdin_text: str) -> str | None:
    """The hook event's session_id when it is a safe value."""
    try:
        event = json.loads(stdin_text)
    except ValueError:
        return None
    return valid_session(event.get("session_id")) if isinstance(event, dict) else None


def _save_session(session: str | None) -> None:
    """Hand the session ID to later commands through Claude Code's env file, when it gives one."""
    target = os.environ.get("CLAUDE_ENV_FILE")
    try:
        if target and session:
            with open(target, "a", encoding="utf-8") as handle:
                handle.write(f"export AFC_SESSION={session}\n")
    except OSError:
        pass  # the welcome must never break over this


def main(stdout=None, stdin_text: str = "") -> int:
    stdout = stdout or sys.stdout
    session = _session_in(stdin_text)
    _save_session(session)
    try:
        home = afc_home()
    except Exception:
        home = Path.home() / ".A-FC"
    out = _with_home_note(build_output(home, session), home)
    stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(stdin_text=sys.stdin.read() if not sys.stdin.isatty() else ""))
