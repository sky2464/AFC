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

from afc import update, version

FETCH_BUDGET = 60  # a release fetch may be bigger than the daily look
MAX_CHANGES = 8


def _refuse(current: str, reason: str) -> dict:
    return {"updated": False, "current": current, "reason": reason}


def _git(root: Path, *args) -> str | None:
    return update._git(root, *args, timeout=FETCH_BUDGET)


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
        return _refuse(current, "Flight Control's own copy has local edits, so nothing was changed; put them away first.")
    tag = update.remote_newest(root, FETCH_BUDGET)
    if tag is None:
        return _refuse(current, "No release could be reached right now, so nothing was changed.")
    if not version.is_newer(tag, current):
        return {"updated": False, "current": current, "reason": f"You already have the newest release, {current}."}
    before = (_git(root, "rev-parse", "HEAD") or "").strip()
    if not before or _git(root, "fetch", "--quiet", "--no-tags", "origin", f"refs/tags/{tag}:refs/tags/{tag}") is None:
        return _refuse(current, f"The release {tag} could not be fetched, so nothing was changed.")
    if _git(root, "merge", "--ff-only", "--quiet", f"{tag}^{{commit}}") is None:
        return _refuse(current, f"{tag} does not continue from your copy, so nothing was changed.")
    log = _git(root, "log", "--format=%s", f"{before}..HEAD") or ""
    changes = [line.strip() for line in log.splitlines() if line.strip()]
    shown = changes[:MAX_CHANGES]
    if len(changes) > len(shown):
        shown.append(f"and {len(changes) - len(shown)} more")
    title = _title(root, tag)
    result = {
        "updated": True, "from": current, "to": tag, "title": title, "changes": shown,
        "check": run_check(root),
    }
    result["summary"] = f"Updated Flight Control from {current} to {tag}: {title}."
    return result
