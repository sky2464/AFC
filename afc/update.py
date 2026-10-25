"""Checking for a newer Flight Control release (FC-011).

A release is a v* tag on the origin remote. The check runs at most once a day; the time and
the newest tag found are kept in the workspace home, with any release the user skipped.
A developer copy (on dev, or in maintenance mode) never offers. Any failure says nothing.
"""

import json
import subprocess
from pathlib import Path

from afc import version
from afc.config import current_session, maintain_enabled

STATE = "update.json"
TIMEOUT = 4
DAY = 86400


def _load(home: Path) -> dict:
    try:
        data = json.loads((home / STATE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(home: Path, data: dict) -> None:
    try:
        home.mkdir(parents=True, exist_ok=True)
        (home / STATE).write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def _git(root: Path, *args) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def remote_newest(root: Path) -> str | None:
    out = _git(root, "ls-remote", "--tags", "--refs", "origin", "v*")
    if out is None:
        return None
    names = [line.split("refs/tags/", 1)[-1].strip() for line in out.splitlines() if "refs/tags/" in line]
    return version.newest(names)


def developer_copy(root: Path, home: Path) -> bool:
    if maintain_enabled(home, current_session()):
        return True
    branch = (_git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
    return branch == "dev"


def skip(home: Path, tag: str) -> None:
    if not version.is_version(tag):
        raise version.VersionError(f"{tag!r} is not a Flight Control version like v0.01a.")
    data = _load(home)
    data["skipped"] = tag
    _save(home, data)


def check(root: Path, home: Path, now: float) -> dict:
    current = version.installed(root)
    quiet = {"update": "none", "current": current}
    if developer_copy(root, home):
        return quiet
    data = _load(home)
    checked = data.get("checked_at")
    if not isinstance(checked, (int, float)) or not 0 <= now - checked < DAY:
        found = remote_newest(root)
        data["checked_at"] = now
        if found:
            data["latest"] = found
        _save(home, data)
    latest = data.get("latest")
    skipped = data.get("skipped")
    if not version.is_version(latest) or not version.is_newer(latest, current):
        return quiet
    if version.is_version(skipped) and not version.is_newer(latest, skipped):
        return quiet
    return {"update": "available", "current": current, "latest": latest}
