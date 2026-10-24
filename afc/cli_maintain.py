"""Maintenance mode command: maintain on|off|status.

Registered into the main parser by afc.cli through register(). Maintenance mode is per session:
it is on only for the session that turned it on, so other sessions keep their usual guard.
"""

import argparse

from afc.config import afc_home, current_session, maintain_scope, set_maintain

NAMES = ("maintain",)
GLOBAL_NOTE = (
    "This session's ID isn't known, so maintenance mode is on for every session until it is "
    "turned off."
)


def register(sub) -> None:
    p = sub.add_parser("maintain", help="turn maintenance mode on, off or show it")
    p.add_argument("state", choices=["on", "off", "status"])
    p.set_defaults(handler=cmd_maintain)


def cmd_maintain(args: argparse.Namespace) -> dict:
    home = afc_home()
    session = current_session()
    if args.state in ("on", "off"):
        set_maintain(home, args.state == "on", session)
    scope = maintain_scope(home, session)
    result: dict = {"maintain": scope != "off", "scope": scope}
    if scope == "global":
        result["note"] = GLOBAL_NOTE if session is None else (
            "Maintenance mode was switched on for every session; turn it off to end that.")
    return result
