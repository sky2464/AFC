"""Maintenance mode command: maintain on|off|status.

Registered into the main parser by afc.cli through register(). Maintenance mode is per session:
it is on only for the session that turned it on, so other sessions keep their usual guard. A tool that
gives no session ID (Cursor, Codex, Copilot) uses a switch for the copy's branch instead. Cursor
chats that expose a conversation ID still honour that branch switch (FC-054).
"""

import argparse

from afc.config import afc_home, current_session, maintain_scope, set_maintain

NAMES = ("maintain",)

_SCOPE_WORDS = {
    "session": "this chat only",
    "branch": "this copy's branch (every Cursor chat on this branch)",
    "off": "off",
}


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
    from afc.cli import CliError  # late import: afc.cli imports this module

    home = afc_home()
    session = current_session()
    if args.state in ("on", "off"):
        try:
            set_maintain(home, args.state == "on", session)
        except ValueError as exc:
            raise CliError(str(exc)) from exc
    scope = maintain_scope(home, session)
    result: dict = {
        "maintain": scope != "off",
        "scope": scope,
        "applies": _SCOPE_WORDS.get(scope, scope),
    }
    if scope != "off":
        result["note"] = "Never on main; type /afc mm off when finished."
    return result
