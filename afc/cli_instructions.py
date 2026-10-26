"""Instructions command: instructions [--write].

Registered into the main parser by afc.cli through register(). Shows whether AGENTS.md and the
Copilot pointer match CLAUDE.md; --write regenerates them. Exits 2 when they are out of date.
"""

import argparse

from afc import instructions
from afc.config import afc_root

NAMES = ("instructions",)


def register(sub) -> None:
    p = sub.add_parser("instructions", help="check or rewrite AGENTS.md from CLAUDE.md")
    p.add_argument("--write", action="store_true", help="rewrite the files that are out of date")
    p.set_defaults(handler=cmd_instructions)


def cmd_instructions(args: argparse.Namespace) -> dict:
    root = afc_root()
    if args.write:
        return {"in_sync": True, "rewrote": [str(p.relative_to(root)) for p in instructions.write(root)]}
    stale = [str(p.relative_to(root)) for p in instructions.out_of_date(root)]
    if stale:
        return {"in_sync": False, "out_of_date": stale, "fix": "sh bin/afc instructions --write", "exit_code": 2}
    return {"in_sync": True}
