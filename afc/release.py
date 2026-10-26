"""Is main ready to tag? (FC-026). Reads local git only and changes nothing."""

import re
import subprocess
from pathlib import Path

from afc import plan, ship, version

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


MAX_LINES = 10


def newest_tag(root: Path) -> str | None:
    """The newest v* tag anywhere (tags sit on main merges, which dev does not contain)."""
    return version.newest((_git(root, "tag", "-l", "v*") or "").split())


def since_tag(root: Path) -> list[str]:
    """Archived spec files that are in HEAD but were not in the newest tag, in id order.

    A tree comparison, because release tags sit on main merge commits that dev never contains,
    so `tag..HEAD` would list the whole history."""
    tag = newest_tag(root)
    args = ["diff", "--diff-filter=A", "--name-only", tag, "HEAD"] if tag else ["ls-tree", "-r", "--name-only", "HEAD"]
    out = _git(root, *args, "--", "docs/specs/archive")
    names = sorted({Path(l.strip()).name for l in (out or "").splitlines()})
    return [n for n in names if re.match(r"FC-\d+-.*\.md$", n)]


def _line(root: Path, name: str) -> str:
    text = (Path(root) / "docs" / "specs" / "archive" / name).read_text(encoding="utf-8")
    sid = name.split("-")[0] + "-" + name.split("-")[1]
    first = text.split("\n", 1)[0]
    title = re.sub(r"^#\s+\S+\s+\S+\s*", "", first).strip() or name[:-3]
    goal = re.sub(r"^## .*\n\n?", "", ship.changelog_entry(text, sid, title, "x").split("\n", 2)[2]).strip()
    goal = goal.split("\n")[0]
    sentence = re.split(r"(?<=[.!?])\s", goal)[0] if goal else title
    if len(sentence) > 200:
        sentence = sentence[:197].rstrip() + "..."
    return f"- {sid} {title}: {sentence}"


def prepare(root: Path, version_name: str, show: bool) -> dict:
    """List the specs done since the newest tag; unless show, write the changelog section and VERSION."""
    root = Path(root)
    if not version.is_version(version_name):
        raise ValueError(f"{version_name!r} is not a version like v0.07a. Give the version you want.")
    names = since_tag(root)
    tag = newest_tag(root)
    lines = [_line(root, n) for n in names]
    room = MAX_LINES - 2
    if len(lines) > room:
        extra = len(lines) - (room - 1)
        lines = lines[: room - 1] + [f"- and {extra} more changes"]
    section = "\n".join([f"## {version_name}", ""] + lines) + "\n"
    result = {"since": tag, "version": version_name, "specs": [n[:-3] for n in names],
              "section": section, "written": False}
    if show or not names:
        if not names:
            result["note"] = "Nothing has been finished since the last release."
        return result
    log = root / "docs" / "changelog.md"
    current = log.read_text(encoding="utf-8") if log.exists() else ""
    if re.search(rf"^##\s+{re.escape(version_name)}\s*$", current, re.MULTILINE):
        raise ValueError(f"The changelog already has a section for {version_name}.")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(ship.add_to_changelog(current, section), encoding="utf-8")
    (root / "VERSION").write_text(version_name + "\n", encoding="utf-8")
    result["written"] = True
    return result
