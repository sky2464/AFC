"""CI status: the last GitHub Actions run of the test workflow, read with `gh` (FC-019 slice 5).

Says nothing rather than guessing: no `gh`, not signed in, no runs or any odd answer is "unknown".
"""

import json
import shutil
import subprocess

BRANCH = "dev"
WORKFLOW = "tests.yml"
FAILED = ("failure", "timed_out", "startup_failure")


def last_run(root, run=subprocess.run, which=shutil.which) -> dict:
    """{'state': 'failed' | 'passed' | 'running' | 'unknown', 'line': str, 'fix_first': bool}."""
    unknown = {"state": "unknown", "line": "", "fix_first": False}
    if which("gh") is None:
        return unknown
    try:
        done = run(["gh", "run", "list", "--workflow", WORKFLOW, "--branch", BRANCH, "--limit", "1",
                    "--json", "status,conclusion,url"],
                   cwd=str(root), capture_output=True, text=True, timeout=10)
        if done.returncode != 0:
            return unknown
        runs = json.loads(done.stdout)
        item = runs[0]
        status, conclusion = item.get("status"), item.get("conclusion")
    except (OSError, subprocess.SubprocessError, ValueError, IndexError, KeyError, AttributeError, TypeError):
        return unknown
    if status != "completed":
        return {"state": "running", "line": "The tests are running on GitHub.", "fix_first": False}
    if conclusion in FAILED:
        url = item.get("url")
        more = f" ({url})" if isinstance(url, str) and url else ""
        return {"state": "failed", "fix_first": True,
                "line": f"The last test run on GitHub failed{more}. Fixing it comes first."}
    if conclusion == "success":
        return {"state": "passed", "line": "The last test run on GitHub passed.", "fix_first": False}
    return unknown
