"""Test command: runs the core tests (FC-030)."""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from afc.config import afc_root

NAMES = ("test", "ci", "gate")


def register(sub) -> None:
    p = sub.add_parser("test", help="run the core tests")
    p.set_defaults(handler=cmd_test)
    c = sub.add_parser("ci", help="show how the last test run on GitHub went")
    c.set_defaults(handler=cmd_ci)
    g = sub.add_parser("gate", help="the build workflow's quick gate for one built slice")
    g.add_argument("--spec", required=True)
    g.add_argument("--slice", required=True, type=int)
    g.add_argument("--base", required=True, help="the commit the slice started from")
    g.set_defaults(handler=cmd_gate)


def cmd_test(args: argparse.Namespace) -> dict:
    """Run the core tests in one process (FC-030)."""
    root = Path(afc_root())
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-t", str(root)],
        cwd=root, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(root)},
    )
    text = proc.stderr + proc.stdout
    ran = re.search(r"^Ran (\d+) tests? in", text, re.M)
    total = int(ran.group(1)) if ran else 0
    bad = len(re.findall(r"^(?:FAIL|ERROR): ", text, re.M))
    if proc.returncode != 0 and not bad:
        bad = 1
    out: dict = {"passed": max(total - bad, 0), "failed": bad, "seconds": round(time.monotonic() - start, 1)}
    if bad:
        out["failure"] = "\n".join(text.strip().splitlines()[-15:])
    out["exit_code"] = 1 if bad else 0
    return out


def cmd_ci(args: argparse.Namespace) -> dict:
    from afc import ci_status

    return ci_status.last_run(Path(afc_root()))


def cmd_gate(args: argparse.Namespace) -> dict:
    from afc import gate

    return gate.quick_gate(Path(afc_root()), Path(args.spec), args.slice, args.base)
