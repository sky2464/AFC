"""Argument parser for sh bin/afc."""

import argparse
import re

from afc import (
    cli_agents,
    cli_awake,
    cli_context,
    cli_connectors,
    cli_defaults,
    cli_delivery,
    cli_guard,
    cli_health,
    cli_home,
    cli_index,
    cli_maintain,
    cli_plan,
    cli_project_setup,
    cli_projects,
    cli_review,
    cli_ship,
    cli_slice,
    cli_test,
    cli_tools,
    cli_version,
)
from afc.cli import COMMAND_NAMES, _Parser


def plain_usage(message: str) -> str:
    choice = re.search(r"argument (\S+): invalid choice: '([^']*)' \(choose from (.*)\)$", message)
    if choice:
        field, value, options = choice.groups()
        items = re.findall(r"'([^']*)'", options) or [o.strip() for o in options.split(",")]
        if field == "command":
            return f"Unknown command {value}. Use one of: {', '.join(items)}."
        return f"Use one of: {', '.join(items)}."
    missing = re.search(r"the following arguments are required: (.*)$", message)
    if missing:
        names = [n.strip() for n in missing.group(1).split(",")]
        if names == ["command"]:
            return f"Missing command. Use one of: {', '.join(COMMAND_NAMES)}."
        return f"Missing {_join_and(names)}."
    needs = re.search(r"argument (\S+): expected one argument", message)
    if needs:
        return f"{needs.group(1)} needs a value."
    unknown = re.search(r"unrecognized arguments: (.*)$", message)
    if unknown:
        return f"Unknown option {unknown.group(1)}."
    return "That command is not valid."


def _join_and(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def build_parser() -> argparse.ArgumentParser:
    from afc import cli

    parser = _Parser(prog="sh bin/afc", description="Flight Control command line.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    p = sub.add_parser("new", help="create a project folder, workspace and registry entry")
    p.add_argument("--name", required=True)
    p.add_argument("--parent", required=True)
    p.add_argument("--git-name", required=True)
    p.add_argument("--git-email", required=True)
    p.add_argument("--ai-trailer", action="store_true")
    p.add_argument("--profile")
    p.set_defaults(handler=cli_project_setup.cmd_new)

    p = sub.add_parser("adopt", help="register an existing folder")
    p.add_argument("--name", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--git-name")
    p.add_argument("--git-email")
    p.set_defaults(handler=cli_project_setup.cmd_adopt)

    p = sub.add_parser("switch", help="make a registered project active")
    p.add_argument("name")
    p.set_defaults(handler=cli.cmd_switch)

    p = sub.add_parser("list", help="list registered projects")
    p.set_defaults(handler=cli.cmd_list)

    p = sub.add_parser("status", help="show the active project")
    p.set_defaults(handler=cli.cmd_status)

    p = sub.add_parser("open", help="open the active workspace (macOS)")
    p.set_defaults(handler=cli.cmd_open)

    p = sub.add_parser("modules", help="rule modules for the active project")
    p.add_argument("--touches", default="")
    p.add_argument("--full", action="store_true", help="the long rule files, for review")
    p.set_defaults(handler=cli.cmd_modules)

    p = sub.add_parser("set", help="change one setting of the active project")
    p.add_argument("field")
    p.add_argument("value")
    p.set_defaults(handler=cli.cmd_set)

    p = sub.add_parser("scan", help="run slice checks and write a report")
    p.add_argument("--slice", required=True)
    p.set_defaults(handler=cli.cmd_scan)

    cli_agents.register(sub)
    cli_connectors.register(sub)
    cli_context.register(sub)
    cli_delivery.register(sub)
    cli_index.register(sub)
    cli_projects.register(sub)
    cli_health.register(sub)
    cli_guard.register(sub)
    cli_maintain.register(sub)
    cli_tools.register(sub)
    cli_plan.register(sub)
    cli_home.register(sub)
    cli_version.register(sub)
    cli_defaults.register(sub)
    cli_review.register(sub)
    cli_ship.register(sub)
    cli_slice.register(sub)
    cli_test.register(sub)
    cli_awake.register(sub)
    return parser
