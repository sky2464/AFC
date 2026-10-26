"""Maintenance mode command: maintain on|off|status.

Registered into the main parser by afc.cli through register(). Maintenance mode is per session:
it is on only for the session that turned it on, so other sessions keep their usual guard.
"""

import argparse

from afc.config import NO_SESSION, afc_home, current_session, maintain_scope, set_maintain

NAMES = ("maintain",)


def register(sub) -> None:
    p = sub.add_parser("maintain", help="turn maintenance mode on, off or show it")
    p.add_argument(
        "state",
        nargs="?",
        choices=["on", "off", "status"],
        default="status",
        help="on, off or status (default: status)",
    )
    p.set_defaults(handler=cmd_maintain)


def cmd_maintain(args: argparse.Namespace) -> dict:
    home = afc_home()
    session = current_session()
    if args.state in ("on", "off"):
        if session is None:  # off must not look like success while the question stays open
            return {"error": NO_SESSION}
        try:
            set_maintain(home, args.state == "on", session)
        except ValueError as exc:
            return {"error": str(exc)}
    scope = maintain_scope(home, session)
    result: dict = {"maintain": scope != "off", "scope": scope}
    return result
