"""Command line for Flight Control: python3 -m afc <command>.

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

from afc.config import afc_home, afc_root, maintain_enabled, set_maintain
from afc.profile import PROFILES, modules_for
from afc.registry import (
    Project,
    RegistryError,
    load_registry,
    save_registry,
    validate_name,
)
from afc.session_dirs import GrantError, check_settings, grant_dirs, settings_path
from afc.undo import Undo
from afc.workspace import create_workspace

TEAM_MODES = ("solo", "team", "unknown")
REMOTES = ("none", "github", "azure")
COMMAND_NAMES = ("new", "adopt", "switch", "list", "status", "open", "maintain", "modules", "set")
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
        raise _UsageError(_plain_usage(message))


def main(argv: list[str]) -> int:
    try:
        args = _build_parser().parse_args(argv)
        result = args.handler(args)
    except (_UsageError, CliError, RegistryError, GrantError, OSError) as exc:
        return _fail(str(exc))
    print(json.dumps(result))
    return 0


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


def cmd_new(args: argparse.Namespace) -> dict:
    home = afc_home()
    reg = load_registry(home)
    name = _new_name(reg, args.name)
    profile = _profile_arg(args.profile)
    parent = Path(args.parent).expanduser().resolve()
    if not parent.is_dir():
        raise CliError(f"Folder {parent} does not exist.")
    code = parent / name
    if code.exists() and (not code.is_dir() or any(code.iterdir())):
        raise CliError(f"Folder {code} already exists and is not empty.")
    readme, ignore = _app_templates()
    if shutil.which("git") is None:
        raise CliError("git is not installed.")

    undo = _settings_undo()
    undo.mark(
        [
            home,
            home / "projects",
            home / "projects" / name,
            settings_path(afc_root()).parent,
            code,
            code / ".git",
            code / "README.md",
            code / ".gitignore",
        ]
    )
    try:
        code.mkdir(exist_ok=True)
        _git_init(code)
        (code / "README.md").write_text(readme.replace("{name}", name), encoding="utf-8")
        (code / ".gitignore").write_bytes(ignore)
        ws = create_workspace(home, name)
        project = Project(
            name=name,
            code_path=str(code),
            workspace_path=str(ws),
            profile=profile,
            git_name=args.git_name,
            git_email=args.git_email,
            ai_trailer=args.ai_trailer,
            last_active=_today(),
        )
        reg.add(project)
        reg.set_active(name)
        granted = _commit(home, reg, code, undo)
    except BaseException:
        undo.rollback()
        raise
    return {**_project_result(project, granted), **_icloud_fields(project, code)}


def cmd_adopt(args: argparse.Namespace) -> dict:
    home = afc_home()
    reg = load_registry(home)
    name = _new_name(reg, args.name)
    path = Path(args.path).expanduser().resolve()
    if not path.is_dir():
        raise CliError(f"Folder {path} does not exist.")

    undo = _settings_undo()
    undo.mark([home, home / "projects", home / "projects" / name, settings_path(afc_root()).parent])
    try:
        ws = create_workspace(home, name)
        project = Project(
            name=name,
            code_path=str(path),
            workspace_path=str(ws),
            git_name=args.git_name or "",
            git_email=args.git_email or "",
            last_active=_today(),
        )
        reg.add(project)
        reg.set_active(name)
        granted = _commit(home, reg, path, undo)
    except BaseException:
        undo.rollback()
        raise
    return {
        **_project_result(project, granted),
        **_icloud_fields(project, path),
        "is_git": (path / ".git").exists(),
    }


def cmd_switch(args: argparse.Namespace) -> dict:
    home = afc_home()
    reg = load_registry(home)
    project = reg.get(args.name)
    if project is None:
        raise CliError(_unknown_name(args.name))
    reg.set_active(args.name)
    reg.update(args.name, last_active=_today())
    undo = _settings_undo()
    try:
        granted = _commit(home, reg, Path(project.code_path), undo)
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
    project = _active(load_registry(afc_home()))
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


def cmd_maintain(args: argparse.Namespace) -> dict:
    home = afc_home()
    if args.state in ("on", "off"):
        set_maintain(home, args.state == "on")
    return {"maintain": maintain_enabled(home)}


def cmd_modules(args: argparse.Namespace) -> dict:
    project = load_registry(afc_home()).active()
    if project is None:
        raise CliError(NO_ACTIVE_INTERVIEW)
    if project.profile not in PROFILES:
        raise CliError(NO_PROFILE_INTERVIEW)
    touches = {t.strip() for t in args.touches.split(",") if t.strip()}
    return {"profile": project.profile, "modules": modules_for(project.profile, touches)}


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


# ------------------------------------------------------------- set helpers


def _one_of(allowed: tuple[str, ...]):
    def check(field: str, raw: str) -> str:
        if raw not in allowed:
            raise CliError(f"{field} must be one of: {', '.join(allowed)}.")
        return raw

    return check


def _true_or_false(field: str, raw: str) -> bool:
    if raw not in ("true", "false"):
        raise CliError(f"{field} must be true or false.")
    return raw == "true"


def _free_text(field: str, raw: str) -> str:
    return raw


SETTABLE = {
    "profile": _one_of(PROFILES),
    "team_mode": _one_of(TEAM_MODES),
    "remote": _one_of(REMOTES),
    "ai_trailer": _true_or_false,
    "last_slice": _free_text,
    "git_name": _free_text,
    "git_email": _free_text,
}


# ----------------------------------------------------------------- helpers


def _settings_undo() -> Undo:
    """Check the settings file before any write, so a corrupt file fails before anything is created."""
    root = afc_root()
    check_settings(root)
    return Undo(settings_path(root))


def _commit(home: Path, reg, code: Path, undo: Undo) -> list[str]:
    """Grant the code path to the session, then save the registry. Caller rolls back on error."""
    undo.save_settings()
    granted = grant_dirs(afc_root(), [code])
    save_registry(home, reg)
    return granted


def _app_templates() -> tuple[str, bytes]:
    src = afc_root() / "templates" / "app"
    return (src / "README.md").read_text(encoding="utf-8"), (src / "gitignore").read_bytes()


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


def _git_init(code: Path) -> None:
    try:
        subprocess.run(
            ["git", "init", "-q", "-b", "main"],
            cwd=code,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CliError("git is not installed.") from exc
    except subprocess.CalledProcessError as exc:
        raise CliError(f"git init failed: {exc.stderr.strip()}") from exc


def _now_text(ws: Path) -> str:
    """Text under '## Now' in plan/progress.md, up to the next heading. Empty if none."""
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


def _plain_usage(message: str) -> str:
    """Turn an argparse complaint into a plain sentence."""
    choice = re.search(r"argument (\S+): invalid choice: '([^']*)' \(choose from (.*)\)$", message)
    if choice:
        field, value, options = choice.groups()
        items = re.findall(r"'([^']*)'", options)
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


def _fail(message: str) -> int:
    print(json.dumps({"error": message}))
    return 1


# ------------------------------------------------------------------ parser


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="python3 -m afc", description="Flight Control command line.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    p = sub.add_parser("new", help="create a project folder, workspace and registry entry")
    p.add_argument("--name", required=True)
    p.add_argument("--parent", required=True)
    p.add_argument("--git-name", required=True)
    p.add_argument("--git-email", required=True)
    p.add_argument("--ai-trailer", action="store_true")
    p.add_argument("--profile")
    p.set_defaults(handler=cmd_new)

    p = sub.add_parser("adopt", help="register an existing folder")
    p.add_argument("--name", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--git-name")
    p.add_argument("--git-email")
    p.set_defaults(handler=cmd_adopt)

    p = sub.add_parser("switch", help="make a registered project active")
    p.add_argument("name")
    p.set_defaults(handler=cmd_switch)

    p = sub.add_parser("list", help="list registered projects")
    p.set_defaults(handler=cmd_list)

    p = sub.add_parser("status", help="show the active project")
    p.set_defaults(handler=cmd_status)

    p = sub.add_parser("open", help="open the active workspace (macOS)")
    p.set_defaults(handler=cmd_open)

    p = sub.add_parser("maintain", help="turn maintenance mode on, off or show it")
    p.add_argument("state", choices=["on", "off", "status"])
    p.set_defaults(handler=cmd_maintain)

    p = sub.add_parser("modules", help="rule modules for the active project")
    p.add_argument("--touches", default="")
    p.set_defaults(handler=cmd_modules)

    p = sub.add_parser("set", help="change one setting of the active project")
    p.add_argument("field")
    p.add_argument("value")
    p.set_defaults(handler=cmd_set)

    return parser
