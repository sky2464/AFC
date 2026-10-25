"""Checking for a newer Flight Control release (FC-011).

A release is a v* tag on the origin remote whose commit is on main: `git ls-remote --tags` lists
the tags, then main is fetched and each tag is kept only if its commit is part of main's history,
so a tag that exists only on dev is never offered. The check runs at most once a day; the time and
the newest tag found are kept in the workspace home, with any release the user skipped.
A developer copy (on dev, or in maintenance mode) never offers. Any failure says nothing, and git
never prompts for a credential or a host key (no terminal, no stdin). Every call may be given a
shorter budget (in seconds) than TIMEOUT, which is how the welcome keeps the check from delaying it.
"""

import json
import os
import subprocess
import time
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


def _quiet_env() -> dict:
    """Git's environment with every way of asking the user for something switched off."""
    env = dict(os.environ)
    env.update(GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="", SSH_ASKPASS_REQUIRE="never")
    return env


def _git(root: Path, *args, timeout: float = TIMEOUT) -> str | None:
    # No stdin, no controlling terminal and no askpass: a private or SSH origin fails quietly
    # instead of printing a credential or host-key prompt.
    try:
        done = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=min(timeout, TIMEOUT),
            stdin=subprocess.DEVNULL, env=_quiet_env(), start_new_session=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def _release_commits(listing: str) -> dict:
    """Tag name -> commit it points at, from `ls-remote --tags` (an annotated tag's ^{} line wins)."""
    direct, peeled = {}, {}
    for line in listing.splitlines():
        sha, _, ref = line.strip().partition("\t")
        if not ref.startswith("refs/tags/"):
            continue
        name = ref[len("refs/tags/"):]
        if name.endswith("^{}"):
            peeled[name[:-3]] = sha
        else:
            direct[name] = sha
    return {name: peeled.get(name, sha) for name, sha in direct.items() if version.is_version(name)}


def remote_newest(root: Path, budget: float = TIMEOUT) -> str | None:
    """The newest v* tag on origin whose commit is part of main's history, or None."""
    budget = min(budget, TIMEOUT)
    deadline = time.monotonic() + budget
    listing = _git(root, "ls-remote", "--tags", "origin", "v*", timeout=budget)
    if listing is None:
        return None
    releases = _release_commits(listing)
    if not releases:
        return None
    left = deadline - time.monotonic()
    if left <= 0 or _git(root, "fetch", "--quiet", "--no-tags", "origin", "refs/heads/main", timeout=left) is None:
        return None
    for name in sorted(releases, key=version.key, reverse=True):
        # exit 0 only when the tag's commit is in main; a commit that is not even present here
        # (it was never part of main) fails the same way
        if _git(root, "merge-base", "--is-ancestor", releases[name], "FETCH_HEAD", timeout=budget) is not None:
            return name
    return None


def developer_copy(root: Path, home: Path, budget: float = TIMEOUT) -> bool:
    if maintain_enabled(home, current_session()):
        return True
    branch = (_git(root, "rev-parse", "--abbrev-ref", "HEAD", timeout=budget) or "").strip()
    return branch == "dev"


def skip(home: Path, tag: str) -> None:
    if not version.is_version(tag):
        raise version.VersionError(f"{tag!r} is not a Flight Control version like v0.01a.")
    data = _load(home)
    data["skipped"] = tag
    _save(home, data)


def check(root: Path, home: Path, now: float, budget: float = TIMEOUT) -> dict:
    current = version.installed(root)
    quiet = {"update": "none", "current": current}
    if developer_copy(root, home, budget):
        return quiet
    data = _load(home)
    checked = data.get("checked_at")
    if not isinstance(checked, (int, float)) or not 0 <= now - checked < DAY:
        found = remote_newest(root, budget)
        data["checked_at"] = now
        if found:
            data["latest"] = found
        else:
            # offline, timed out, failed, or nothing released any more: an older answer is not
            # offered again, the welcome says nothing
            data.pop("latest", None)
        _save(home, data)
    latest = data.get("latest")
    skipped = data.get("skipped")
    if not version.is_version(latest) or not version.is_newer(latest, current):
        return quiet
    if version.is_version(skipped) and not version.is_newer(latest, skipped):
        return quiet
    return {"update": "available", "current": current, "latest": latest}
