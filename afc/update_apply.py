"""Applying a Flight Control update (FC-011 slice 4).

`apply` moves the A-FC folder to the newest release tag with a fast-forward only: no merge commit,
no history rewrite, no force. It refuses, leaving the folder untouched, when the folder has local
edits, is not on main, or is a developer copy, and says why in one sentence. After the update it
runs `sh bin/afc check` (the new code's own health check) and reports what changed in plain words.
"""

import json
import os
import subprocess
from pathlib import Path

from afc import connectors, update, version
from afc.cli_health import ADDONS

NOTE = "just_updated.json"  # one-time note in the workspace home for the welcome after a restart
# What Claude Code reads only at session start: a change to any of these needs a restart.
SESSION_START_FILES = ("CLAUDE.md", ".claude/settings.json", ".claude/skills/", ".claude/commands/", "afc/hooks/")
RESTART_HOW = (
    "The new version takes effect after a restart: type /exit, then run `claude --continue` in the "
    "A-FC folder to come back to this same conversation."
)
FETCH_BUDGET = 60  # a release fetch may be bigger than the daily look
MAX_CHANGES = 8


def _refuse(current: str, reason: str) -> dict:
    return {"updated": False, "current": current, "reason": reason}


def _git(root: Path, *args) -> str | None:
    return update._git(root, *args, timeout=FETCH_BUDGET, cap=FETCH_BUDGET)


def run_check(root: Path) -> dict | None:
    """Run `sh bin/afc check` in the updated folder; None when it can't be run or read."""
    try:
        done = subprocess.run(
            ["sh", "bin/afc", "check"], cwd=root, capture_output=True, text=True, timeout=FETCH_BUDGET,
            stdin=subprocess.DEVNULL, env=dict(os.environ),
        )
        out = json.loads(done.stdout)
        return out if isinstance(out, dict) else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def run_upgrade(root: Path, old_version: str) -> dict | None:
    """Run the new code's workspace upgrade (`sh bin/afc upgrade`); None when it can't be run or read."""
    try:
        done = subprocess.run(
            ["sh", "bin/afc", "upgrade", "--from-version", old_version], cwd=root, capture_output=True,
            text=True, timeout=FETCH_BUDGET, stdin=subprocess.DEVNULL, env=dict(os.environ),
        )
        out = json.loads(done.stdout)
        return out if isinstance(out, dict) else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def needs_restart(changed: list[str]) -> bool:
    """True when any changed file is one Claude only reads at session start."""
    return any(path == f or (f.endswith("/") and path.startswith(f)) for path in changed for f in SESSION_START_FILES)


def leave_note(home: Path, tag: str) -> bool:
    """Leave the one-time 'just updated to vX' note for the next welcome; False when it can't be written."""
    try:
        home.mkdir(parents=True, exist_ok=True)
        (home / NOTE).write_text(json.dumps({"version": tag}), encoding="utf-8")
        return True
    except OSError:
        return False


def take_note(home: Path) -> str | None:
    """The version in the note, which is removed as it is read (shown once); None when there is none."""
    path = home / NOTE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tag = data.get("version") if isinstance(data, dict) else None
    except (OSError, ValueError):
        tag = None
    try:
        path.unlink()
    except OSError:
        pass
    return tag if isinstance(tag, str) else None


def _asked(home: Path) -> list[str]:
    ws = None
    try:
        from afc.registry import load_registry

        project = load_registry(home).active()
        ws = Path(project.workspace_path) if project else None
    except Exception:
        pass
    return connectors.asked_full(home, ws)


def _title(root: Path, tag: str) -> str:
    out = _git(root, "tag", "-l", "--format=%(contents:subject)", tag)
    title = (out or "").strip()
    return title or tag


def apply(root: Path, home: Path) -> dict:
    root = Path(root)
    try:
        current = version.installed(root)
    except version.VersionError as exc:
        return _refuse("", str(exc))
    if update.developer_copy(root, home):
        return _refuse(current, "This is a developer copy of Flight Control, so it is not updated here.")
    if update._branch(root) != "main":
        return _refuse(current, "Flight Control's own copy is not on main, so nothing was changed; put it back on main first.")
    status = update._git(root, "status", "--porcelain")
    if status is None:
        return _refuse(current, "Git could not read Flight Control's own copy, so nothing was changed.")
    if status.strip():
        lines = [l for l in status.splitlines() if l.strip()]
        if all(l.startswith("??") for l in lines):
            paths = [l[3:].strip() for l in lines[:3]]
            named = ", ".join(paths)
            tail = f" ({named})" if named else ""
            return _refuse(
                current,
                f"Flight Control's own copy has new files git is not tracking{tail},"
                " so nothing was changed; put them away or remove them first.",
            )
        return _refuse(current, "Flight Control's own copy has local edits, so nothing was changed; put them away first.")
    tag = update.remote_newest(root, FETCH_BUDGET)
    if tag is None:
        return _refuse(current, "No release could be reached right now, so nothing was changed.")
    if not version.is_newer(tag, current):
        return {"updated": False, "current": current, "reason": f"You already have the newest release, {current}."}
    before = (_git(root, "rev-parse", "HEAD") or "").strip()
    wanted = _asked(home)
    old_settings = connectors.unhide(root)  # a plain-words connector choice is put back after the merge
    hidden = old_settings is not None

    def _restore() -> None:
        if hidden:
            try:
                connectors.restore_hidden(root, old_settings)
            except Exception:
                pass

    # fetched without a local tag (it lands in FETCH_HEAD only), so a refused update leaves no trace
    if not before or _git(root, "fetch", "--quiet", "--no-tags", "origin", f"refs/tags/{tag}") is None:
        _restore()
        return _refuse(current, f"The release {tag} could not be fetched, so nothing was changed.")
    if _git(root, "merge", "--ff-only", "--quiet", "FETCH_HEAD^{commit}") is None:
        _restore()
        return _refuse(current, f"{tag} does not continue from your copy, so nothing was changed.")
    kept_note = ""
    if hidden:
        try:
            connectors.rehide(root, wanted)
        except Exception:
            kept_note = (
                " Your choice to keep a connector turned on could not be applied to the new settings,"
                " so the file was left as released and the connector may be off again; ask me to turn the connector on again."
            )
    # the update is in: now keep the tag too (its objects are already here)
    _git(root, "fetch", "--quiet", "--no-tags", "origin", f"refs/tags/{tag}:refs/tags/{tag}")
    log = _git(root, "log", "--format=%s", f"{before}..HEAD") or ""
    changes = [line.strip() for line in log.splitlines() if line.strip()]
    shown = changes[:MAX_CHANGES]
    if len(changes) > len(shown):
        shown.append(f"and {len(changes) - len(shown)} more")
    title = _title(root, tag)
    changed = (_git(root, "diff", "--name-only", f"{before}..HEAD") or "").split("\n")
    restart = needs_restart([c.strip() for c in changed if c.strip()])
    leave_note(home, tag)
    result = {
        "updated": True, "from": current, "to": tag, "title": title, "changes": shown,
        "check": run_check(root),
        "restart": restart,
    }
    if restart:
        result["restart_how"] = RESTART_HOW
    result["summary"] = f"Updated Flight Control from {current} to {tag}: {title}." + kept_note
    result["workspace"] = run_upgrade(root, current)
    ws = result["workspace"]
    if isinstance(ws, dict) and ws.get("summary"):
        result["summary"] += " " + ws["summary"]
    elif not isinstance(ws, dict):
        result["summary"] += (
            " Your workspace upgrade could not be run or read, so check it by running the upgrade again"
            " (sh bin/afc upgrade)."
        )
    said = check_sentence(result["check"])
    if said:
        result["summary"] += " " + said
    return result


def check_sentence(check: dict | None) -> str:
    """The health check after an update in one sentence: add-ons counted, never named; other
    problems counted with the first shown. The full list stays in the JSON."""
    if not isinstance(check, dict):
        return ""
    problems = [p for p in check.get("problems") or [] if isinstance(p, dict)]
    if not problems:
        return "Everything checks out." if check.get("ok") is not False else ""
    addons = sum(1 for p in problems if p.get("kind") in ADDONS)
    others = [p for p in problems if p.get("kind") not in ADDONS]
    parts = []
    if others:
        first = str(others[0].get("detail") or others[0].get("kind")).split(". ")[0].rstrip(".")
        if len(others) == 1:
            parts.append(f"1 thing needs a look: {first}")
        else:
            parts.append(f"{len(others)} things need a look, first: {first}, and {len(others) - 1} more")
    if addons:
        noun = "add-on" if addons == 1 else "add-ons"
        parts.append(f"{addons} {noun} will be off in Flight Control sessions from the next start")
    return "; ".join(parts) + "."
