"""Run the test suite one process per test file, in parallel (FC-019). Standard library only."""

import ast
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_RAN = re.compile(r"^Ran (\d+) tests? in", re.M)
_BAD = re.compile(r"^(?:FAIL|ERROR): (.+)$", re.M)


SHARED = ("tests/helpers.py", "tests/__init__.py", "bin/afc", ".claude/settings.json")
SHARED_DIRS = ("afc/hooks/",)


def _imports(path: Path) -> set[str]:
    """Dotted module names a test file imports, including `from pkg import mod` as pkg.mod."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{a.name}" for a in node.names)
    return found


def pick_tests(changed: list[str], top: Path, tests_dir: Path) -> list[str]:
    """Test file names that cover the changed files; everything for shared files or no match."""
    everything = sorted(p.name for p in Path(tests_dir).glob("test_*.py"))
    if any(c in SHARED or c.startswith(SHARED_DIRS) for c in changed):
        return everything
    picked: set[str] = set()
    for name in everything:
        path = Path(tests_dir) / name
        text = path.read_text(encoding="utf-8", errors="replace")
        imports = _imports(path)
        for c in changed:
            if c.startswith("tests/"):
                if Path(c).name == name:
                    picked.add(name)
            elif c.endswith(".py"):
                mod = c[:-3].replace("/", ".")
                if mod in imports or any(i.startswith(mod + ".") for i in imports):
                    picked.add(name)
                elif c in text:
                    picked.add(name)
            elif c in text or Path(c).name in text:
                picked.add(name)
    return sorted(picked) if picked else everything


def changed_files(top: Path, ref: str) -> list[str]:
    """Files changed since ref, including uncommitted ones."""
    proc = subprocess.run(["git", "diff", "--name-only", ref], cwd=top, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ValueError(f"git could not compare with {ref}: {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line]


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
