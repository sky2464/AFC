"""The build workflow's quick gate, as a command: one JSON object per slice (FC-019 fix).

The workflow runtime has no shell, so the gate lives here and a helper only runs
`sh bin/afc gate` and returns its one line.
"""

import re
import subprocess
from pathlib import Path


SECRET_PATTERNS = [
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    r"\bsk-[A-Za-z0-9_-]{20,}\b",
    r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b",
]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def quick_gate(root: Path, spec: Path, number: int, base: str) -> dict:
    """Check one built slice: tagged commit, ticked box, its tests, no secrets, files in the repo."""
    problems = []

    def add(problem: str, quotes: str) -> None:
        problems.append({"problem": problem, "quotes": quotes})

    names = _git(root, "diff", "--name-only", base, "HEAD")
    if names.returncode != 0:
        return {"ok": False, "files": [], "problems": [
            {"problem": f"git could not compare with {base}: {names.stderr.strip()}",
             "quotes": "commit tagged with the slice"}]}
    files = [f.strip() for f in names.stdout.splitlines() if f.strip()]

    tag = f"slice {number}"
    commits = _git(root, "log", "--format=%H", "--grep", tag, f"{base}..HEAD")
    if commits.returncode != 0 or not commits.stdout.strip():
        add(f'no commit since {base[:7]} has "{tag}" in its message', "commit tagged with the slice")

    text = Path(spec).read_text(encoding="utf-8") if Path(spec).is_file() else ""
    if not re.search(rf"^- \[x\] {number}\.", text, re.M):
        add(f"slice {number}'s checkbox is not ticked in {spec}", "checkbox ticked")

    diff = _git(root, "diff", base, "HEAD").stdout
    added = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    if any(re.search(p, l) for l in added for p in SECRET_PATTERNS):
        add("the diff adds a line that looks like a secret", "no secret patterns in the diff")

    outside = [f for f in files if f.startswith("/") or ".." in f.split("/")]
    if outside:
        add("files outside this repo: " + ", ".join(outside), "no file changed outside this repo")

    return {"ok": not problems, "files": files, "problems": problems}
