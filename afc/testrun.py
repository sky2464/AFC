"""Run the test suite one process per test file, in parallel (FC-019). Standard library only."""

import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_RAN = re.compile(r"^Ran (\d+) tests? in", re.M)
_BAD = re.compile(r"^(?:FAIL|ERROR): (.+)$", re.M)


def _run_one(top: Path, tests_dir: Path, name: str) -> tuple[int, list[str]]:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(tests_dir), "-t", str(top), "-p", name],
        cwd=top, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(top)},
    )
    out = proc.stderr + proc.stdout
    ran = _RAN.search(out)
    bad = _BAD.findall(out)
    if proc.returncode != 0 and not bad:
        bad = [f"{name} (did not run)"]
    return (int(ran.group(1)) if ran else 0), [f"{name}: {b}" for b in bad]


def run_files(top: Path, tests_dir: Path, names: list[str] | None = None, jobs: int | None = None) -> dict:
    """Run each test file (all test_*.py in tests_dir, or names) and sum up the results."""
    start = time.monotonic()
    names = names if names is not None else sorted(p.name for p in Path(tests_dir).glob("test_*.py"))
    with ThreadPoolExecutor(max_workers=jobs or os.cpu_count() or 4) as pool:
        results = list(pool.map(lambda n: _run_one(Path(top), Path(tests_dir), n), names))
    failures = [f for _, fs in results for f in fs]
    return {
        "files": len(names),
        "tests": sum(n for n, _ in results),
        "failed": len(failures),
        "seconds": round(time.monotonic() - start, 1),
        "failures": failures,
    }
