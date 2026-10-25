"""Test command: test runs every test file in parallel (FC-019)."""

import argparse
from pathlib import Path

from afc import testrun
from afc.config import afc_root

NAMES = ("test",)


def register(sub) -> None:
    p = sub.add_parser("test", help="run the test suite, one process per file, in parallel")
    p.add_argument("--dir", help="a folder of test_*.py files to run instead of tests/")
    p.add_argument("--changed", metavar="REF", help="run only the tests for files changed since REF")
    p.add_argument("--list", action="store_true", help="with --changed, show the picked tests without running them")
    p.set_defaults(handler=cmd_test)


def cmd_test(args: argparse.Namespace) -> dict:
    from afc.cli import CliError

    root = Path(afc_root())
    if args.changed:
        try:
            changed = testrun.changed_files(root, args.changed)
        except ValueError as exc:
            raise CliError(str(exc))
        picked = testrun.pick_tests(changed, root, root / "tests")
        if args.list:
            return {"changed": changed, "picked": picked}
        out = testrun.run_files(root, root / "tests", picked)
        out["picked"] = len(picked)
    elif args.dir:
        out = testrun.run_files(Path(args.dir), Path(args.dir))
    else:
        out = testrun.run_files(root, root / "tests")
    out["exit_code"] = 1 if out["failed"] else 0
    return out
