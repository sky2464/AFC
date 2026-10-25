"""SessionStart hook: greet the user with the first question and tell Claude about the projects.

The welcome line already asks the first question with options 1 and 2, so the user can answer with
one key. The context line tells Claude what 1 and 2 mean.

When a newer Flight Control release is out (FC-011), the first question is the update one: a notice
line and "1. Update now (recommended)  2. Not now". The project question follows once it is answered.
The welcome never waits for the network: it uses the answer saved by the daily look for a release,
which runs in the background (afc.update) and is there from the next start.

Never fails: any problem reading the registry becomes a context line, a problem with the update
check leaves it out, and main returns 0.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from afc import update, update_apply, version
from afc.config import afc_home, afc_root, maintain_enabled, valid_session
from afc.context_brief import brief_path
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
    if active is not None:
        brief = brief_path(Path(active.workspace_path))
        if brief.is_file():
            project += f" Compact context: {brief} — read once per slice, not intent+architecture separately."
    others = [n for n in reg.ready() if active is None or n != active.name]
    paused = f" Paused: {', '.join(reg.paused())}." if reg.paused() else ""
    return f"{project} Other projects: {', '.join(others) or 'none'}.{paused}"


def _health_line(home: Path) -> str:
    """A short note when the health check finds problems, so Claude can mention them."""
    try:
        from afc.cli_health import find_problems

        count = len(find_problems(home, with_addons=False))  # the welcome handles add-ons itself
    except Exception:  # the welcome must never break over a health check
        return ""
    if not count:
        return ""
    noun = "problem" if count == 1 else "problems"
    return (f" Health check: {count} {noun} (sh bin/afc check). After answering the first message, "
            "mention it in one line and offer to look.")


def _addons_line(root: Path) -> str:
    """Switch off the add-ons that aren't on the allowed list, and say so in one line. Empty when
    there was nothing to do or anything failed: the settings are then as they were."""
    try:
        from afc.cli_health import addon_problems, switch_addons

        off, _ = switch_addons(root, addon_problems(root))
    except Exception:  # the welcome must never break over add-ons
        return ""
    if not off:
        return ""
    one = off == 1
    return (f"🔌 {off} add-on{'' if one else 's'} {'isn' if one else 'aren'}'t on Flight Control's list, "
            f"so {'it is' if one else 'they are'} off in its sessions from the next start. "
            f"{'It still works' if one else 'They still work'} everywhere else.\n")


def _update_offer(home: Path, now: float | None = None) -> tuple[str, str] | None:
    """(installed, newest) when a newer release is on offer, else None. Never waits for the network
    and never raises: whatever goes wrong with the check, the welcome simply says nothing about
    updates."""
    try:
        found = update.offer(afc_root(), home, now=time.time() if now is None else now)
        if found.get("update") != "available":
            return None
        current, latest = found["current"], found["latest"]
        if not (isinstance(current, str) and isinstance(latest, str)):
            return None
        return current, latest
    except Exception:  # the welcome must never break over an update check
        return None


def _just_updated(home: Path) -> str:
    """'You're on vX now.' once after an update, then the note is removed. Never raises."""
    try:
        tag = update_apply.take_note(home)
        if tag and tag == version.installed(afc_root()):
            return f"You're on {tag} now.\n"
    except Exception:  # the welcome must never break
        pass
    return ""


def _update_message(current: str, latest: str) -> str:
    return (f"{INTRO}\nFlight Control {latest} is out; you have {current}.\n"
            "1. Update now (recommended)  2. Not now")


def _update_question(current: str, latest: str, one: str, two: str) -> str:
    """What Claude is told when the welcome asked the update question instead of the project one."""
    return (
        f"A newer Flight Control release is out: {latest} (installed {current}). The welcome asked "
        "the update question first: 1 = update now, 2 = not now. If the first message is 1, run "
        "sh bin/afc update and tell the user in plain words what happened; if the result says restart is "
        "true, say the new version takes effect after a restart and give its restart_how (type /exit, "
        "then run claude --continue in the A-FC folder). If it is 2, run "
        f"sh bin/afc update --skip {latest}, say you will stay quiet until a newer release, then "
        f"ask the project question (1 = {one}, 2 = {two}). For anything else, answer it briefly, "
        "then ask the update question. Never ask both questions in one message.")


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
        f"{INTRO}\n{_addons_line(root)}🔧 Maintenance: working on Flight Control itself · {root.name} · {branch}\n"
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
    launcher = afc_root() / "bin" / "afc"
    context = f"{context} Run Flight Control with: sh {launcher} <command>."
    return {
        "systemMessage": message,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context},
    }


def build_output(home: Path, session: str | None = None, now: float | None = None) -> dict:
    if maintain_enabled(home, session):
        try:
            return _maintenance_output()
        except Exception:  # the welcome must never break
            pass
    try:
        reg = load_registry(home)
        one, two, line = _choices(reg)
        offer = _update_offer(home, now)
        gone = _just_updated(home)
        if offer:
            message = _update_message(*offer)
            asked = _update_question(*offer, one, two)
        else:
            message = f"{INTRO}\n{line}"
            asked = (
                f"The welcome asked: 1 = {one}, 2 = {two}. "
                "If the user's first message is 1 or 2, treat it as their answer — do not ask that "
                "question again. If they said hi or asked something else, answer briefly, then ask "
                f"one question: 1 = {one} (recommended) or 2 = {two}."
            )
        message = message.replace(f"{INTRO}\n", f"{INTRO}\n{gone}{_addons_line(afc_root())}", 1)
        context = (
            f"Flight Control session. {_project_line(reg)} {asked}{_health_line(home)} "
            "Follow CLAUDE.md and the afc-start skill for the first reply."
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
