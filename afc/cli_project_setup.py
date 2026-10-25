"""New and adopted projects: create folders, agents and brief."""

import argparse
import shutil
import subprocess
from pathlib import Path

from afc.config import afc_home, afc_root
from afc.context_brief import refresh as refresh_context_brief
from afc.project_agents import install_code_agents
from afc.registry import Project, load_registry, save_registry
from afc.session_dirs import settings_path
from afc.workspace import create_workspace


def bootstrap_project(code: Path, workspace: Path, profile: str) -> dict:
    agents = install_code_agents(code, workspace, profile)
    brief = refresh_context_brief(workspace, profile=profile)
    return {"agents": agents, "brief": brief}


def _app_templates() -> tuple[str, bytes]:
    src = afc_root() / "templates" / "app"
    return (src / "README.md").read_text(encoding="utf-8"), (src / "gitignore").read_bytes()


def _git_init(code: Path) -> None:
    from afc.cli import CliError

    try:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=code, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CliError("git is not installed.") from exc
    except subprocess.CalledProcessError as exc:
        raise CliError(f"git init failed: {exc.stderr.strip()}") from exc


def cmd_new(args: argparse.Namespace) -> dict:
    from afc.cli import (
        CliError,
        _commit,
        _icloud_fields,
        _new_name,
        _profile_arg,
        _project_result,
        _settings_undo,
        _today,
    )

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
        granted = _commit(home, reg, project, undo)
        setup = bootstrap_project(code, ws, profile)
    except BaseException:
        undo.rollback()
        raise
    return {**_project_result(project, granted), **_icloud_fields(project, code), **setup}


def cmd_adopt(args: argparse.Namespace) -> dict:
    from afc.cli import (
        CliError,
        _commit,
        _icloud_fields,
        _new_name,
        _project_result,
        _settings_undo,
        _today,
    )

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
        granted = _commit(home, reg, project, undo)
        setup = bootstrap_project(path, ws, project.profile or "personal")
    except BaseException:
        undo.rollback()
        raise
    return {
        **_project_result(project, granted),
        **_icloud_fields(project, path),
        "is_git": (path / ".git").exists(),
        **setup,
    }
