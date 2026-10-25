"""Test command: test runs every test file in parallel (FC-019)."""

import argparse
from pathlib import Path

from afc import testrun
from afc.config import afc_root

NAMES = ("test",)


def register(sub) -> None:
    p = sub.add_parser("test", help="run the test suite, one process per file, in parallel")
    p.add_argument("--dir", help="a folder of test_*.py files to run instead of tests/")
    p.set_defaults(handler=cmd_test)


def cmd_test(args: argparse.Namespace) -> dict:
    root = Path(afc_root())
    if args.dir:
        out = testrun.run_files(Path(args.dir), Path(args.dir))
    else:
        out = testrun.run_files(root, root / "tests")
    out["exit_code"] = 1 if out["failed"] else 0
    return out
