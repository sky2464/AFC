"""Command line for Flight Control: sh bin/afc <command>.

Every command prints one JSON object on stdout. Success exits 0. Failure prints
{"error": "<message>"} and exits 1. Skills and the welcome flow call these
commands, so the output keys are a contract.
"""

import argparse
import dataclasses
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from afc.config import afc_home, afc_root
from afc.profile import PROFILES, modules_for
from afc import (
    cli_agents,
    cli_awake,
    cli_connectors,
    cli_context,
    cli_defaults,
    cli_delivery,
    cli_health,
    cli_home,
    cli_index,
    cli_maintain,
    cli_plan,
    cli_projects,
    cli_review,
    cli_ship,
    cli_slice,
    cli_test,
    cli_tools,
    cli_version,
    scan,
)
from afc.registry import (
    PAUSED,
    Project,
    RegistryError,
    load_registry,
    save_registry,
    validate_name,
)
from afc.cli_settings import SETTABLE, SettingError
from afc.session_dirs import GrantError, check_settings, grant_dirs, settings_path
from afc import tools
from afc.undo import Undo
from afc.workspace import create_workspace

COMMAND_NAMES = (
    "new",
    "adopt",
    "switch",
    "list",
    "status",
    "open",
    "modules",
    "set",
    "scan",
    *cli_defaults.NAMES,
    *cli_agents.NAMES,
    *cli_connectors.NAMES,
    *cli_context.NAMES,
    *cli_delivery.NAMES,
    *cli_home.NAMES,
    *cli_index.NAMES,
    *cli_plan.NAMES,
    *cli_projects.NAMES,
    *cli_health.NAMES,
    *cli_review.NAMES,
    *cli_ship.NAMES,
    *cli_slice.NAMES,
    *cli_tools.NAMES,
    *cli_test.NAMES,
    *cli_maintain.NAMES,
    *cli_version.NAMES,
    *cli_awake.NAMES,
)
ICLOUD_WARNING = (
    "This folder syncs to iCloud. Work and enterprise code should not sync, "
    "so move the project to a folder that is not synced."
)
NO_ACTIVE = "No active project — type /afc to see your projects."
NO_ACTIVE_INTERVIEW = "No active project — finish the setup interview first."
NO_PROFILE_INTERVIEW = "This project has no profile yet — finish the setup interview first."
HEADING_RE = re.compile(r"^#{1,6}\s")


class CliError(Exception):
    """A user-facing failure. The message is shown as the JSON error."""


class _UsageError(Exception):
    """Bad arguments, already in plain words. Raised instead of argparse printing."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        from afc.cli_parser import plain_usage

        raise _UsageError(plain_usage(message))


def main(argv: list[str]) -> int:
    try:
        from afc.cli_parser import build_parser

        args = build_parser().parse_args(argv)
        result = args.handler(args)
    except (_UsageError, CliError, SettingError, RegistryError, GrantError, OSError) as exc:
        return _fail(str(exc))
    code = result.pop("exit_code", 0) if isinstance(result, dict) else 0
    print(json.dumps(result))
    return code


def icloud_synced(path: Path) -> bool:
    """True when path sits in an iCloud-synced location.

    That is ~/Library/Mobile Documents/ itself, or ~/Documents and ~/Desktop while
    iCloud Drive's Documents folder exists (Desktop & Documents sync is on).
    """
    home = Path.home().resolve()
    mobile = home / "Library" / "Mobile Documents"
    target = path.resolve()
    if target.is_relative_to(mobile):
        return True
    if (mobile / "com~apple~CloudDocs" / "Documents").exists():
        return any(target.is_relative_to(home / name) for name in ("Documents", "Desktop"))
    return False


# ---------------------------------------------------------------- commands


def cmd_switch(args: argparse.Namespace) -> dict:
    home = afc_home()
    reg = load_registry(home)
    project = reg.get(args.name)
    if project is None:
        raise CliError(_unknown_name(args.name))
    if project.status == PAUSED:
        raise CliError(f"{project.name} is paused. Resume it to work on it again.")
    reg.set_active(args.name)
    reg.update(args.name, last_active=_today())
    undo = _settings_undo()
    try:
        granted = _commit(home, reg, project, undo)
    except BaseException:
        undo.rollback()
        raise
    return _project_result(project, granted)


def cmd_list(args: argparse.Namespace) -> dict:
    reg = load_registry(afc_home())
    return {
        "active": reg.active_name,
        "projects": [dataclasses.asdict(p) for p in reg.projects.values()],
    }


def cmd_status(args: argparse.Namespace) -> dict:
    reg = load_registry(afc_home())
    if reg.active() is None:
        result: dict = {"active": None, "projects": reg.ready()}
        if reg.paused():
            result["paused"] = reg.paused()
        return result
    project = _active(reg)
    data = dataclasses.asdict(project)
    data["now"] = _now_text(Path(project.workspace_path))
    return data


def cmd_open(args: argparse.Namespace) -> dict:
    project = _active(load_registry(afc_home()))
    ws = project.workspace_path
    if sys.platform != "darwin":
        return {"opened": False, "path": ws}
    try:
        subprocess.run(["open", ws], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        raise CliError(f"Could not open {ws}.") from exc
    return {"opened": True, "path": ws}


def cmd_modules(args: argparse.Namespace) -> dict:
    project = load_registry(afc_home()).active()
    if project is None:
        raise CliError(NO_ACTIVE_INTERVIEW)
    if project.profile not in PROFILES:
        raise CliError(NO_PROFILE_INTERVIEW)
    touches = {t.strip() for t in args.touches.split(",") if t.strip()}
    names = modules_for(project.profile, touches)
    rules = afc_root() / "rules"
    folder = rules if args.full else rules / "short"
    return {"profile": project.profile, "modules": names, "form": "full" if args.full else "short",
            "paths": {name: str(folder / f"{name}.md") for name in names}}


def cmd_set(args: argparse.Namespace) -> dict:
    home = afc_home()
    reg = load_registry(home)
    project = _active(reg)
    if args.field not in SETTABLE:
        raise CliError(f"Unknown setting {args.field}. Choose one of: {', '.join(SETTABLE)}.")
    value = SETTABLE[args.field](args.field, args.value)
    reg.update(project.name, **{args.field: value})
    save_registry(home, reg)
    result = {"project": project.name, "field": args.field, "value": value}
    if args.field == "profile":
        warning = _icloud_warning(value, icloud_synced(Path(project.code_path)))
        if warning:
            result["warning"] = warning
    return result


def cmd_scan(args: argparse.Namespace) -> dict:
    project = _active(load_registry(afc_home()))
    checks = scan.run_checks(Path(project.code_path))
    report = scan.write_report(Path(project.workspace_path), checks, args.slice)
    return {"summary": scan.summary_line(checks), "report": str(report)}


# ----------------------------------------------------------------- helpers


def _settings_undo() -> Undo:
    """Check the settings file before any write, so a corrupt file fails before anything is created."""
    root = afc_root()
    check_settings(root)
    return Undo(settings_path(root))


def _commit(home: Path, reg, project: Project, undo: Undo) -> list[str]:
    """Grant the project's code and workspace to the session (replacing earlier grants),
    then save the registry. Caller rolls back on error."""
    undo.save_settings()
    undo.on_rollback(tools.snapshot(afc_root()))
    granted = grant_dirs(afc_root(), [Path(project.code_path), Path(project.workspace_path)])
    try:
        tools.swap_in(afc_root(), Path(project.workspace_path))
    except tools.ToolsError as exc:
        raise CliError(str(exc))
    save_registry(home, reg)
    return granted


def _new_name(reg, raw: str) -> str:
    validate_name(raw)
    if raw in reg.projects:
        raise CliError(f"A project named {raw} already exists — type /afc to see your projects.")
    return raw


def _profile_arg(raw: str | None) -> str:
    if raw is None:
        return "unknown"
    if raw not in PROFILES:
        raise CliError(f"profile must be one of: {', '.join(PROFILES)}.")
    return raw


def _unknown_name(name: str) -> str:
    return f"No project named {name} — type /afc to see your projects."


def _active(reg) -> Project:
    project = reg.active()
    if project is None:
        raise CliError(NO_ACTIVE)
    return project


def _today() -> str:
    return date.today().isoformat()


def _project_result(project: Project, granted: list[str]) -> dict:
    return {
        "project": project.name,
        "code_path": project.code_path,
        "workspace_path": project.workspace_path,
        "granted": granted,
    }


def _icloud_fields(project: Project, folder: Path) -> dict:
    synced = icloud_synced(folder)
    fields: dict = {"icloud_synced": synced}
    warning = _icloud_warning(project.profile, synced)
    if warning:
        fields["warning"] = warning
    return fields


def _icloud_warning(profile: str, synced: bool) -> str | None:
    if synced and profile in ("work", "enterprise"):
        return ICLOUD_WARNING
    return None


def _now_text(ws: Path) -> str:
    """The active spec from the master plan; else text under '## Now' in plan/progress.md."""
    from afc.plan import now_line

    line = now_line(ws)
    if line:
        return line
    path = ws / "plan" / "progress.md"
    if not path.exists():
        return ""
    lines: list[str] = []
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if HEADING_RE.match(line):
            if inside:
                break
            inside = line.strip() == "## Now"
            continue
        if inside:
            lines.append(line)
    return "\n".join(lines).strip()


def _fail(message: str) -> int:
    print(json.dumps({"error": message}))
    return 1


