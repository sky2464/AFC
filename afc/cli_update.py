"""Version command: sh bin/afc version prints the version of this copy of Flight Control.

Registered into the main parser by afc.cli through register(). Read-only: it reads the VERSION
file at the root of the A-FC repo.
"""

import argparse

from afc import version
from afc.config import afc_root

NAMES = ("version",)


def register(sub) -> None:
    p = sub.add_parser("version", help="show the version of this copy of Flight Control")
    p.set_defaults(handler=cmd_version)


def _cli():
    from afc import cli  # late import: afc.cli imports this module

    return cli


def cmd_version(args: argparse.Namespace) -> dict:
    try:
        found = version.read(afc_root())
    except version.VersionError as exc:
        raise _cli().CliError(str(exc)) from exc
    return {"version": found.label()}
