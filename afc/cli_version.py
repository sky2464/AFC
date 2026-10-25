"""Version command: version prints the installed Flight Control version (FC-011)."""

import argparse
import time

from afc import update, version
from afc.config import afc_home, afc_root

NAMES = ("version", "update")


def register(sub) -> None:
    p = sub.add_parser("version", help="show the installed Flight Control version")
    p.set_defaults(handler=cmd_version)
    u = sub.add_parser("update", help="check for a newer Flight Control release")
    u.add_argument("--check", action="store_true", help="only check, change nothing")
    u.add_argument("--skip", metavar="VERSION", help="stay quiet about this release")
    u.set_defaults(handler=cmd_update)


def _fail(exc):
    from afc import cli  # late import: afc.cli imports this module

    raise cli.CliError(str(exc)) from None


def cmd_update(args: argparse.Namespace) -> dict:
    try:
        if args.skip:
            update.skip(afc_home(), args.skip)
            return {"skipped": args.skip}
        if not args.check:
            _fail("Updating itself is not ready yet; use update --check.")
        return update.check(afc_root(), afc_home(), now=time.time())
    except version.VersionError as exc:
        _fail(exc)


def cmd_version(args: argparse.Namespace) -> dict:
    try:
        return {"version": version.installed(afc_root())}
    except version.VersionError as exc:
        from afc import cli  # late import: afc.cli imports this module

        raise cli.CliError(str(exc)) from None
