"""Ship command: sh bin/afc ship --check <id>.

Registered into the main parser by afc.cli through register(). It reports the readiness gate
for the spec in Now and changes nothing at all.
"""

import argparse
from pathlib import Path

from afc import ship
from afc.config import afc_home, afc_root, current_session, maintain_enabled
from afc.registry import load_registry

NAMES = ("ship",)


def register(sub) -> None:
    p = sub.add_parser("ship", help="check that a spec is finished (changes nothing)")
    p.add_argument("--check", required=True, metavar="ID")
    p.set_defaults(handler=cmd_ship)


def cmd_ship(args: argparse.Namespace) -> dict:
    from afc import cli_plan

    space, _, text = cli_plan._load()
    section, row = cli_plan._find(space, text, args.check)
    if section != "Now":
        raise cli_plan._error(f"{args.check} isn't in progress.")
    _, spec_text = cli_plan._read_spec(space, args.check, row)
    return {"id": args.check, **run_gate(spec_text)}


def run_gate(spec_text: str) -> dict:
    """The readiness gate for the active plan's code folder (Flight Control's own in maintenance)."""
    from afc import cli

    home = afc_home()
    if maintain_enabled(home, current_session()):
        return ship.gate(spec_text, afc_root(), None, run_tests=False)
    else:
        project = cli._active(load_registry(home))
        code, command = Path(project.code_path), ship.recorded_test_command(Path(project.workspace_path))
    return ship.gate(spec_text, code, command)
