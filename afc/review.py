"""Slice review: the scan checks, a verdict, and a report beside the scan reports.

afc.scan runs the checks. A check that failed is critical and holds the slice; a warning is
written down; a missing tool counts as neither. The verdict is blocked while anything is
critical, and ok otherwise. The report is written whatever the verdict, so every slice leaves
a trail. Later slices of FC-014 add their own checks to the same list.

Two checks are the review's own. A changed file over 500 lines is critical and named. A line of
the active spec's "You'll know it works when" list that no test mentions is critical and quoted
in full. A line is covered when one test file holds most of its words.
"""

import re
import subprocess
from pathlib import Path

from afc import plan, scan
from afc.scan import Check

MAX_LINES = 500
_STOP = {"when", "then", "that", "with", "this", "from", "which", "into", "does", "have",
         "will", "your", "they", "them", "their", "than", "once", "only", "each", "also"}
_TEST_FILE = re.compile(r"(^|/)(tests?|__tests__)/|(^|/)test_[^/]*\.py$|_test\.\w+$|\.(test|spec)\.\w+$")

OK = "ok"
BLOCKED = "blocked"


def _changed_files(code: Path) -> list[Path]:
    """Tracked and untracked changes in the code folder, the set deliver would commit."""
    done = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=code, capture_output=True,
                          text=True)
    names = [line[3:].split(" -> ")[-1].strip('"') for line in done.stdout.splitlines()]
    return [code / n for n in names if (code / n).is_file()]


def file_size_checks(code: Path) -> list[Check]:
    checks = []
    for path in _changed_files(code):
        try:
            count = len(path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            continue
        if count > MAX_LINES:
            rel = path.relative_to(code).as_posix()
            checks.append(Check("file size", "fail", f"{rel} has {count} lines, over {MAX_LINES}"))
    return checks


def active_spec(workspace: Path) -> Path | None:
    """The spec in the project plan's Now row, or None."""
    space = plan.project_space(workspace)
    if not space.master.is_file():
        return None
    rows = plan.read_rows(space.master.read_text(encoding="utf-8"), "Now")
    m = re.search(r"\(([^)]*)\)", rows[0][3]) if rows and len(rows[0]) > 3 else None
    spec = space.base / m.group(1) if m else None
    return spec if spec and spec.is_file() else None


def acceptance_lines(spec_text: str) -> list[str]:
    """The bullets under 'You'll know it works when', each joined onto one line."""
    out, inside = [], False
    for line in spec_text.splitlines():
        if line.startswith("## "):
            inside = "know it works when" in line
        elif inside and line.startswith("- "):
            out.append(line[2:].strip())
        elif inside and out and line.startswith(" ") and line.strip():
            out[-1] += " " + line.strip()
    return out


def _words(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in _STOP}


def acceptance_checks(code: Path, spec: Path) -> list[Check]:
    tests = []
    for path in code.rglob("*"):
        rel = path.relative_to(code).as_posix()
        if path.is_file() and ".git/" not in rel and _TEST_FILE.search(rel):
            try:
                tests.append(_words(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                pass
    checks = []
    for line in acceptance_lines(spec.read_text(encoding="utf-8")):
        want = _words(line)
        if not any(want and len(want & have) >= 0.6 * len(want) for have in tests):
            checks.append(Check("untested acceptance line", "fail", f"no test behind: {line}"))
    return checks


def regression_checks(code: Path, label: str) -> list[Check]:
    """A bug-fix slice (its label says fix or bug) needs a changed test file that names a regression."""
    if not re.search(r"\b(fix|fixes|fixed|bug|bugs|bugfix|hotfix)\b", label.lower()):
        return []
    for path in _changed_files(code):
        if _TEST_FILE.search(path.relative_to(code).as_posix()):
            try:
                if re.search(r"regression", path.read_text(encoding="utf-8"), re.I):
                    return []
            except (OSError, UnicodeDecodeError):
                pass
    return [Check("regression test", "fail", f"bug fix '{label}' has no regression test named after the bug")]


def run_review(code_path: Path, workspace_path: Path, label: str) -> dict:
    """Run the checks on the code folder, write the report, and return the verdict and counts."""
    code = Path(code_path)
    checks = scan.run_checks(code) + file_size_checks(code) + regression_checks(code, label)
    spec = active_spec(Path(workspace_path))
    if spec:
        checks += acceptance_checks(code, spec)
    critical = sum(1 for c in checks if c.status == "fail")
    warning = sum(1 for c in checks if c.status == "warn")
    verdict = BLOCKED if critical else OK
    report = scan.write_report(Path(workspace_path), checks, label, verdict=verdict)
    return {"verdict": verdict, "critical": critical, "warning": warning, "report": str(report)}
