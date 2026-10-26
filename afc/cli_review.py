"""Review command: sh bin/afc review --slice "<n> <label>".

Registered into the main parser by afc.cli through register(). It runs the slice checks on the
active project's code folder, gives a verdict, and writes the report to the project's reports
folder beside the scan reports. A blocked verdict is a result, not a failure, so it exits 0.
"""

import argparse
from pathlib import Path

from afc import review
from afc.config import afc_home
from afc.registry import load_registry

NAMES = ("review",)


def register(sub) -> None:
    p = sub.add_parser("review", help="review the slice: checks, verdict and report")
    p.add_argument("--slice", required=True)
    p.add_argument("--tests", action="store_true",
                   help="also demand a test behind each acceptance line and for a fix")
    p.set_defaults(handler=cmd_review)


def _cli():
    from afc import cli  # late import: afc.cli imports this module

    return cli


def cmd_review(args: argparse.Namespace) -> dict:
    project = _cli()._active(load_registry(afc_home()))
    return review.run_review(Path(project.code_path), Path(project.workspace_path), args.slice,
                            tests=args.tests)
