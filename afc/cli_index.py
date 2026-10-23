"""Index commands: index rebuild|refresh|search|findings, graph impact.

Registered into the main parser by afc.cli through register(). Each handler
returns one JSON-able dict, like every other Flight Control command.
"""

import argparse
import sqlite3
from pathlib import Path

from afc import index
from afc.config import afc_home
from afc.registry import load_registry

NAMES = ("index", "graph")


def register(sub) -> None:
    p = sub.add_parser("index", help="build or query the search index")
    isub = p.add_subparsers(dest="index_command", required=True)
    q = isub.add_parser("rebuild", help="rebuild the active project's index (--all: cross-project)")
    q.add_argument("--all", action="store_true")
    q.set_defaults(handler=cmd_rebuild)
    q = isub.add_parser("refresh", help="update the active project's index")
    q.set_defaults(handler=cmd_refresh)
    q = isub.add_parser("search", help="search plans and resources")
    q.add_argument("query")
    q.add_argument("--all", action="store_true")
    q.set_defaults(handler=cmd_search)
    q = isub.add_parser("findings", help="open findings across all projects")
    q.add_argument("--all", action="store_true", required=True)
    q.set_defaults(handler=cmd_findings)

    p = sub.add_parser("graph", help="ask the code graph")
    gsub = p.add_subparsers(dest="graph_command", required=True)
    q = gsub.add_parser("impact", help="what would changing NAME affect")
    q.add_argument("name")
    q.set_defaults(handler=cmd_impact)


def _error(message: str) -> Exception:
    from afc.cli import CliError  # late import: afc.cli imports this module

    return CliError(message)


def _active():
    from afc.cli import NO_ACTIVE

    project = load_registry(afc_home()).active()
    if project is None:
        raise _error(NO_ACTIVE)
    return Path(project.workspace_path), project.name


def _project_db() -> Path:
    ws, name = _active()
    return index.refresh_project_index(ws, name)


def _global_db() -> Path:
    home = afc_home()
    db = home / index.INDEX_NAME
    if db.exists():
        try:
            index.open_index(db).close()
            return db
        except (sqlite3.DatabaseError, index.IndexSchemaError):
            pass
    return index.rebuild_global_index(home)


def cmd_rebuild(args: argparse.Namespace) -> dict:
    if args.all:
        return {"index": str(index.rebuild_global_index(afc_home())), "scope": "all"}
    ws, name = _active()
    return {"index": str(index.rebuild_project_index(ws, name)), "scope": name}


def cmd_refresh(args: argparse.Namespace) -> dict:
    ws, name = _active()
    return {"index": str(index.refresh_project_index(ws, name)), "scope": name}


def cmd_search(args: argparse.Namespace) -> dict:
    db = _global_db() if args.all else _project_db()
    return {"query": args.query, "results": index.search(db, args.query)}


def cmd_findings(args: argparse.Namespace) -> dict:
    return {"findings": index.open_findings(_global_db())}


def cmd_impact(args: argparse.Namespace) -> dict:
    return {"name": args.name, "matches": index.neighbors(_project_db(), args.name)}
