"""The readiness gate for finishing a spec (FC-015).

gate() lists, in plain words, what is still missing before a spec can be called finished. It
only reads: it looks at the spec and at git, and changes nothing. It runs no tests and needs
no test command (FC-030).
"""

import re
import subprocess
from pathlib import Path

from afc import plan



def open_slices(spec_text: str) -> list[str]:
    open_ = plan.open_slices(spec_text)
    if not open_ and not plan.all_slices(spec_text):
        return ["The spec has no slices yet."]
    return [f"A slice is not ticked: {s}" for s in open_]


def clean_tree(code: Path) -> list[str]:
    done = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=code, capture_output=True,
                          text=True)
    if done.returncode != 0:
        return ["The code folder is not a readable git repository."]
    changed = [l for l in done.stdout.splitlines() if l.strip()]
    if changed:
        return [f"There are uncommitted changes in the code folder ({len(changed)} file(s))."]
    return []


WIP_RE = re.compile(r"^wip\b", re.I)


def _git(code: Path, *args: str) -> str | None:
    done = subprocess.run(["git", *args], cwd=code, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def _upstream(code: Path) -> str | None:
    return _git(code, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")


def wip_commits(code: Path) -> list[str]:
    """Name any `WIP` commit on the branch; squashing them is the user's own history rewrite."""
    branch = _git(code, "rev-parse", "--abbrev-ref", "HEAD")
    if not branch:
        return []
    head = _git(code, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    default = head.split("/", 1)[1] if head else None
    base = None
    if default and default != branch and _git(code, "rev-parse", "--verify", "--quiet", head):
        base = head
    elif default and default != branch and _git(code, "rev-parse", "--verify", "--quiet", default):
        base = default
    else:
        base = _upstream(code)
    rng = [f"{base}..HEAD"] if base else ["HEAD"]
    out = _git(code, "log", "--format=%h %s", *rng)
    found = [l for l in (out or "").splitlines() if WIP_RE.match(l.split(" ", 1)[-1])]
    if not found:
        return []
    return [f"{len(found)} `WIP` commit(s) are still on the branch ({'; '.join(found[:3])}). "
            "Squash or reword them yourself (for example `git rebase -i`); Flight Control does not "
            "rewrite history."]


def pushed(code: Path) -> list[str]:
    """On a project with a remote, the branch must be fully pushed."""
    if not _git(code, "remote"):
        return []
    branch = _git(code, "rev-parse", "--abbrev-ref", "HEAD") or "HEAD"
    step = f"Push it yourself with `git push -u origin {branch}`."
    if not _upstream(code):
        return [f"The branch {branch} is not pushed yet. {step}"]
    ahead = _git(code, "rev-list", "--count", "@{u}..HEAD")
    if ahead and ahead != "0":
        return [f"The branch {branch} has {ahead} commit(s) not pushed. {step}"]
    return []


def gate(spec_text: str, code: Path) -> dict:
    """What is missing before the spec is finished; ready only when nothing is."""
    missing = [*open_slices(spec_text), *clean_tree(code),
               *wip_commits(code), *pushed(code)]
    return {"ready": not missing, "missing": missing,
            "next": "Ready to finish." if not missing else missing[0]}


CHANGELOG_HEAD = "# Changelog\n"


def changelog_entry(spec_text: str, sid: str, title: str, today: str) -> str:
    """One entry in the user's words: the date, the spec's goal and the slices that shipped.

    Written from the Goal section and the slice labels, never from commit subjects."""
    lines = spec_text.split("\n")
    goal = ""
    try:
        start, end = plan._section_span(lines, "Goal")
        paragraph: list[str] = []
        for line in lines[start:end]:
            if line.strip():
                paragraph.append(line.strip())
            elif paragraph:
                break
        goal = " ".join(paragraph)
    except ValueError:
        pass
    out = [f"## {today} — {sid} {title}", ""]
    if goal:
        out += [goal, ""]
    for _, label in plan.all_slices(spec_text):
        label = re.sub(r"^\d+\.\s*", "", label)
        label = re.split(r"\s+—\s+you'll (?:check|see)", label)[0].strip()
        out.append(f"- {label}")
    return "\n".join(out) + "\n"


def add_to_changelog(current: str, entry: str) -> str:
    """Put the entry first, under the heading; one entry per spec, newest on top."""
    body = current if current.strip() else CHANGELOG_HEAD
    head, _, rest = body.partition("\n## ")
    head = head.rstrip("\n") + "\n"
    return head + "\n" + entry + (("\n## " + rest) if rest else "")
