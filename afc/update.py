"""Checking for a newer Flight Control release (FC-011).

A release is a v* tag on the origin remote whose commit is on main: `git ls-remote --tags` lists
the tags, then main is fetched and each tag is kept only if its commit is part of main's history,
so a tag that exists only on dev is never offered. The whole look at origin shares one time budget
(TIMEOUT seconds, however many git calls it takes), and git never prompts for a credential or a
host key (no terminal, no stdin). It runs at most once a day; the time and the newest tag found
are kept in the workspace home, with any release the user skipped. A developer copy (on dev, or in
maintenance mode) never offers. Any failure says nothing.

The welcome never waits for the network. `offer` answers from what is saved and, when the day's
look is due, claims the day and starts the look as a separate background process (`python -m
afc.update`) that saves what it finds for the next start. `check` runs the same look in front, for
`sh bin/afc update --check`.
"""

import json
import os
import subprocess
import sys
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


def _save(home: Path, data: dict) -> bool:
    """Write the saved state; False when it could not be written. The write is all at once, so a
    session reading it while another writes it sees the old state or the new, never half of one."""
    temp = home / f"{STATE}.{os.getpid()}.tmp"
    try:
        home.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(temp, home / STATE)
        return True
    except OSError:
        try:
            temp.unlink()
        except OSError:
            pass
        return False


def _quiet_env() -> dict:
    """Git's environment with every way of asking the user for something switched off."""
    env = dict(os.environ)
    env.update(GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="", SSH_ASKPASS_REQUIRE="never")
    return env


def _git(root: Path, *args, timeout: float = TIMEOUT, cap: float = TIMEOUT) -> str | None:
    # No stdin, no controlling terminal and no askpass: a private or SSH origin fails quietly
    # instead of printing a credential or host-key prompt. No time left means no call at all.
    if timeout <= 0:
        return None
    try:
        done = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=min(timeout, cap),
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
    """The newest v* tag on origin whose commit is part of main's history, or None.

    The git calls share one budget (the daily look uses TIMEOUT seconds, an update asks for more):
    each gets the time that is left, and none starts once it has run out."""
    deadline = time.monotonic() + budget

    def run(*args):
        return _git(root, *args, timeout=deadline - time.monotonic(), cap=budget)

    listing = run("ls-remote", "--tags", "origin", "v*")
    if listing is None:
        return None
    releases = _release_commits(listing)
    if not releases or run("fetch", "--quiet", "--no-tags", "origin", "refs/heads/main") is None:
        return None
    for name in sorted(releases, key=version.key, reverse=True):
        # exit 0 only when the tag's commit is in main; a commit that is not even present here
        # (it was never part of main) fails the same way
        if run("merge-base", "--is-ancestor", releases[name], "FETCH_HEAD") is not None:
            return name
    return None


def _branch(root: Path) -> str:
    """The branch the folder is on, read from .git/HEAD: nothing to run, nothing to wait for. Empty
    when it can't be told (detached, no repository, unreadable)."""
    try:
        git_dir = Path(root) / ".git"
        if git_dir.is_file():  # a linked worktree points at its git folder
            pointer = git_dir.read_text(encoding="utf-8").strip()
            if pointer.startswith("gitdir:"):
                git_dir = Path(root) / pointer[len("gitdir:"):].strip()
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return ""
    prefix = "ref: refs/heads/"
    return head[len(prefix):] if head.startswith(prefix) else ""


def developer_copy(root: Path, home: Path) -> bool:
    return maintain_enabled(home, current_session()) or _branch(root) == "dev"


def skip(home: Path, tag: str) -> None:
    if not version.is_version(tag):
        raise version.VersionError(f"{tag!r} is not a Flight Control version like v0.01a.")
    data = _load(home)
    data["skipped"] = tag
    _save(home, data)


def _due(data: dict, now: float) -> bool:
    checked = data.get("checked_at")
    return not isinstance(checked, (int, float)) or not 0 <= now - checked < DAY


def _answer(current: str, data: dict) -> dict:
    """What the saved state says about a newer release."""
    quiet = {"update": "none", "current": current}
    latest = data.get("latest")
    skipped = data.get("skipped")
    if not version.is_version(latest) or not version.is_newer(latest, current):
        return quiet
    if version.is_version(skipped) and not version.is_newer(latest, skipped):
        return quiet
    return {"update": "available", "current": current, "latest": latest}


def refresh(root: Path, home: Path, now: float, budget: float = TIMEOUT) -> dict:
    """Look at origin now and save what it says; returns the saved state."""
    found = remote_newest(root, budget)
    data = _load(home)  # read again: a release may have been skipped while the look ran
    data["checked_at"] = now
    if found:
        data["latest"] = found
    else:
        # offline, timed out, failed, or nothing released any more: an older answer is not
        # offered again, the welcome says nothing
        data.pop("latest", None)
    _save(home, data)
    return data


def check(root: Path, home: Path, now: float, budget: float = TIMEOUT) -> dict:
    """The answer, looking at origin first (and waiting for it) when the day's look is due."""
    current = version.installed(root)
    if developer_copy(root, home):
        return {"update": "none", "current": current}
    data = _load(home)
    if _due(data, now):
        data = refresh(root, home, now, budget)
    return _answer(current, data)


def start_refresh(root: Path, home: Path, now: float) -> subprocess.Popen | None:
    """Start the look at origin as its own process and return at once; None if it can't start.
    The process has no terminal and no output, and ends by itself within TIMEOUT seconds."""
    package_parent = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(package_parent), env.get("PYTHONPATH")) if p)
    try:
        return subprocess.Popen(
            [sys.executable, "-m", "afc.update", str(root), str(home), repr(float(now))],
            cwd=package_parent, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    except (OSError, ValueError):
        return None


def offer(root: Path, home: Path, now: float) -> dict:
    """The answer for the welcome, which never waits for the network.

    It is the saved answer. When the day's look is due, the day is claimed first (so sessions that
    start together don't each start one), the saved answer is kept, and the look starts in
    the background: its result is there from the next start on. A release found earlier is still
    offered meanwhile (the user may start one session a day), unless the look then finds none."""
    current = version.installed(root)
    quiet = {"update": "none", "current": current}
    if developer_copy(root, home):
        return quiet
    data = _load(home)
    if not _due(data, now):
        return _answer(current, data)
    data["checked_at"] = now
    if _save(home, data):  # a workspace that can't be written would start a look on every start
        start_refresh(root, home, now)
    return _answer(current, data)


def _background(argv: list[str]) -> int:
    try:
        refresh(Path(argv[0]), Path(argv[1]), float(argv[2]))
    except Exception:  # nobody reads this process's output: a look that fails says nothing
        pass
    return 0


if __name__ == "__main__":
    sys.exit(_background(sys.argv[1:]))
