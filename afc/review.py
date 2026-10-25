"""Slice review: the scan checks, a verdict, and a report beside the scan reports.

afc.scan runs the checks. A check that failed is critical and holds the slice; a warning is
written down; a missing tool counts as neither. The verdict is blocked while anything is
critical, and ok otherwise. The report is written whatever the verdict, so every slice leaves
a trail. Later slices of FC-014 add their own checks to the same list.
"""

from pathlib import Path

from afc import scan

OK = "ok"
BLOCKED = "blocked"


def run_review(code_path: Path, workspace_path: Path, label: str) -> dict:
    """Run the checks on the code folder, write the report, and return the verdict and counts."""
    checks = scan.run_checks(Path(code_path))
    critical = sum(1 for c in checks if c.status == "fail")
    warning = sum(1 for c in checks if c.status == "warn")
    verdict = BLOCKED if critical else OK
    report = scan.write_report(Path(workspace_path), checks, label, verdict=verdict)
    return {"verdict": verdict, "critical": critical, "warning": warning, "report": str(report)}
