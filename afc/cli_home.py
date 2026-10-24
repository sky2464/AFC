"""Home command: home shows the workspace folder this copy of Flight Control uses.

The launcher (bin/afc) works out where the folder comes from: AFC_HOME, the path in the copy's
.afc-home file, or the default. It passes that as AFC_HOME_SOURCE.
"""

import argparse
import os

from afc.config import afc_home

NAMES = ("home",)
SOURCES = ("env", "file", "default")


def register(sub) -> None:
    p = sub.add_parser("home", help="show the workspace folder this copy uses")
    p.set_defaults(handler=cmd_home)


def cmd_home(args: argparse.Namespace) -> dict:
    source = os.environ.get("AFC_HOME_SOURCE")
    if source not in SOURCES:
        source = "env" if os.environ.get("AFC_HOME") else "default"
    return {"home": str(afc_home()), "source": source}
