"""Version command: version prints the installed Flight Control version (FC-011)."""

import argparse
import time

from afc import release, update, update_apply, version, workspace_upgrade
from afc.config import afc_home, afc_root

NAMES = ("version", "update", "upgrade", "release")


def register(sub) -> None:
    p = sub.add_parser("version", help="show the installed Flight Control version")
    p.set_defaults(handler=cmd_version)
    u = sub.add_parser("update", help="update Flight Control to the newest release")
    u.add_argument("--check", action="store_true", help="only look for a newer release; nothing is updated")
    u.add_argument("--skip", metavar="VERSION", help="stay quiet about this release")
    u.set_defaults(handler=cmd_update)
    r = sub.add_parser("release", help="check whether main is ready to tag; changes nothing")
    r.add_argument("action", choices=["check"])
    r.set_defaults(handler=cmd_release)
    g = sub.add_parser("upgrade", help="upgrade the workspace to the layout this release expects")
    g.add_argument("--from-version", default=None,
                   help="the version being left, for the backup name (default: the installed version)")
    g.set_defaults(handler=cmd_upgrade)


def _fail(exc):
    from afc import cli  # late import: afc.cli imports this module

    raise cli.CliError(str(exc)) from None


def cmd_update(args: argparse.Namespace) -> dict:
    try:
        if args.skip:
            update.skip(afc_home(), args.skip)
            return {"skipped": args.skip}
        if not args.check:
            return update_apply.apply(afc_root(), afc_home())
        return update.check(afc_root(), afc_home(), now=time.time())
    except version.VersionError as exc:
        _fail(exc)


def cmd_version(args: argparse.Namespace) -> dict:
    try:
        return {"version": version.installed(afc_root())}
    except version.VersionError as exc:
        from afc import cli  # late import: afc.cli imports this module

        raise cli.CliError(str(exc)) from None


def cmd_release(args: argparse.Namespace) -> dict:
    return release.check(afc_root())


def cmd_upgrade(args: argparse.Namespace) -> dict:
    old = args.from_version
    if not old:
        try:
            old = version.installed(afc_root())
        except version.VersionError:
            old = "unknown"
    return workspace_upgrade.upgrade(afc_home(), old)
