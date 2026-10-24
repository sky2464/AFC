"""Tool commands: addons.

Registered into the main parser by afc.cli through register().
"""

import argparse

from afc import addons

NAMES = ("addons",)


def register(sub) -> None:
    p = sub.add_parser("addons", help="which account add-ons Flight Control sessions allow")
    p.set_defaults(handler=cmd_addons)


def cmd_addons(args: argparse.Namespace) -> dict:
    from afc import cli  # late import: afc.cli imports this module

    root = cli.afc_root()
    try:
        ok = addons.allowed(root)
    except ValueError as exc:
        raise cli.CliError(str(exc))
    off, note = addons.blocked(root)
    out = {"allowed": ok, "blocked": off, "unknown_state": note is not None}
    if note:
        out["note"] = note
    return out
