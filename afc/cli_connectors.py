"""Connector list commands: `connectors` shows the active project's list, `connectors add <name>`.

Registered into the main parser by afc.cli through register(). The list is kept in the project's
workspace; see afc.connectors.
"""

import argparse
from pathlib import Path

from afc import connectors
from afc.config import afc_home, afc_root
from afc.registry import load_registry

NAMES = ("connectors",)


def register(sub) -> None:
    p = sub.add_parser("connectors", help="show or add the connectors the active project uses")
    p.add_argument("action", nargs="?", choices=["add"], default=None)
    p.add_argument("name", nargs="*", help="connector name, for example Gmail")
    p.set_defaults(handler=cmd_connectors)


def cmd_connectors(args: argparse.Namespace) -> dict:
    from afc.cli import CliError

    project = load_registry(afc_home()).active()
    if project is None:  # no project yet: the workspace-wide list in ~/.A-FC
        if args.action != "add":
            if args.name:
                raise CliError("Use `connectors` to show the list or `connectors add <name>`.")
            data = connectors.load(afc_home())
            return {"project": None, "connectors": connectors.names(data),
                    "found": data.get("found", []), "named": data.get("named", [])}
        ws, code = afc_home(), None
    else:
        ws, code = Path(project.workspace_path), Path(project.code_path)
    if args.action == "add":
        try:
            data, new = connectors.add(ws, " ".join(args.name))
        except ValueError as exc:
            raise CliError(str(exc)) from exc
        released = False
        try:
            released = connectors.release(afc_root(), " ".join(args.name))
        except Exception:  # the list is saved; the block is then lifted by the next start
            pass
        return {"project": project.name if project else None,
                "connectors": connectors.names(data), "added": new,
                "unblocked": released, "applies": "from the next start",
                "now": "or right away from /mcp"}
    if args.name:
        raise CliError("Use `connectors` to show the list or `connectors add <name>`.")
    data = connectors.refresh(ws, code)
    return {"project": project.name, "connectors": connectors.names(data),
            "found": data["found"], "named": data["named"]}
