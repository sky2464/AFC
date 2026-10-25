"""Is main ready to tag? (FC-026). Reads local git only and changes nothing."""

import re
import subprocess
from pathlib import Path

from afc import version

HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\b|^##\s+(v\S+)", re.MULTILINE)


def _git(root, *args):
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _has_entry(root: Path, current: str, tag: str) -> bool:
    try:
        text = (Path(root) / "docs" / "changelog.md").read_text(encoding="utf-8")
    except OSError:
        return False
    since = _git(root, "log", "-1", "--format=%cs", tag) or ""
    for date, named in HEADING.findall(text):
        if named == current or (date and date > since):
            return True
    return False


def check(root: Path) -> dict:
    problems = []
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        problems.append(f"You are not on main (you are on {branch or 'no branch'}).")
    if _git(root, "status", "--porcelain"):
        problems.append("There are uncommitted changes.")
    try:
        current = version.installed(root)
    except version.VersionError as exc:
        problems.append(str(exc))
        current = None
    if current:
        tag = version.newest_release(root, "main")
        if tag and not version.is_newer(current, tag):
            problems.append(f"VERSION says {current}, which is not newer than the newest release {tag}.")
        if tag and not _has_entry(root, current, tag):
            problems.append(f"The changelog has no entry since {tag}.")
        if _git(root, "tag", "-l", current):
            problems.append(f"A tag {current} already exists.")
    return {"ready": not problems, "problems": problems}
