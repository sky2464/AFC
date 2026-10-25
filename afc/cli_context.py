"""Compact project context brief."""

import argparse

from afc.config import afc_home
from afc.context_brief import refresh
from afc.registry import load_registry

NAMES = ("context",)


def register(sub) -> None:
    p = sub.add_parser("context", help="refresh the compact project brief")
    p.set_defaults(handler=cmd_refresh)
    psub = p.add_subparsers(dest="context_cmd")
    ref = psub.add_parser("refresh", help="rewrite resources/afc-brief.md")
    ref.set_defaults(handler=cmd_refresh)


def _active():
    from afc.cli import NO_ACTIVE, CliError

    reg = load_registry(afc_home())
    project = reg.active()
    if project is None:
        raise CliError(NO_ACTIVE)
    return project


def cmd_refresh(args: argparse.Namespace) -> dict:
    project = _active()
    return refresh(project.workspace_path, profile=project.profile or "personal")
