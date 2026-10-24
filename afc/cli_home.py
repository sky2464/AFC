"""Home command: home shows the workspace folder this copy of Flight Control uses.

The launcher (bin/afc) works out where the folder comes from: AFC_HOME, the path in the copy's
.afc-home file, or the default. It passes that as AFC_HOME_SOURCE. `home set` and `home clear`
change the file, which lives in the Flight Control folder, so they need maintenance mode.
"""

import argparse
import os
import re

from afc.config import afc_home, afc_root, current_session, maintain_enabled

NAMES = ("home",)
SOURCES = ("env", "file", "default")
FULL_PATH = re.compile(r"^(/|[A-Za-z]:[\\/])")


def register(sub) -> None:
    p = sub.add_parser("home", help="show or change the workspace folder this copy uses")
    p.set_defaults(handler=cmd_home)
    hsub = p.add_subparsers(dest="home_command")
    q = hsub.add_parser("set", help="use this folder as the workspace for this copy")
    q.add_argument("path")
    q.set_defaults(handler=cmd_set)
    q = hsub.add_parser("clear", help="go back to the default workspace")
    q.set_defaults(handler=cmd_clear)


def _error(message: str) -> Exception:
    from afc import cli  # late import: afc.cli imports this module

    return cli.CliError(message)


def _need_maintenance() -> None:
    if not maintain_enabled(afc_home(), current_session()):
        raise _error("Changing the test home changes Flight Control itself, so it needs "
                     "maintenance mode. Type /afc mm first.")


def cmd_home(args: argparse.Namespace) -> dict:
    source = os.environ.get("AFC_HOME_SOURCE")
    if source not in SOURCES:
        source = "env" if os.environ.get("AFC_HOME") else "default"
    return {"home": str(afc_home()), "source": source}


def cmd_set(args: argparse.Namespace) -> dict:
    _need_maintenance()
    if not FULL_PATH.match(args.path):
        raise _error("Give a full folder path, starting with / or a drive letter like C:.")
    (afc_root() / ".afc-home").write_text(args.path + "\n", encoding="utf-8")
    return {"home_file": args.path, "note": "Takes effect from the next command or session."}


def cmd_clear(args: argparse.Namespace) -> dict:
    _need_maintenance()
    path = afc_root() / ".afc-home"
    existed = path.exists()
    path.unlink(missing_ok=True)
    return {"cleared": existed}
