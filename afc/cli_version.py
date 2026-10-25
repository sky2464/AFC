"""Version command: version prints the installed Flight Control version (FC-011)."""

import argparse

from afc import version
from afc.config import afc_root

NAMES = ("version",)


def register(sub) -> None:
    p = sub.add_parser("version", help="show the installed Flight Control version")
    p.set_defaults(handler=cmd_version)


def cmd_version(args: argparse.Namespace) -> dict:
    try:
        return {"version": version.installed(afc_root())}
    except version.VersionError as exc:
        from afc import cli  # late import: afc.cli imports this module

        raise cli.CliError(str(exc)) from None
