"""Defaults command: what Flight Control can work out before it asks a new project's questions.

Read-only. It names the parent folder to recommend (never an iCloud-synced one), and the git
identity to state instead of asking: the most recently used project's, else git's own global one.
"""

import argparse
import subprocess
from pathlib import Path

from afc.config import afc_home
from afc.registry import load_registry

NAMES = ("defaults",)
PARENT_FOLDERS = ("Code", "Developer", "Projects")
SUGGESTED_FOLDER = "Code"


def register(sub) -> None:
    p = sub.add_parser("defaults", help="show the folder and git identity a new project would use")
    p.set_defaults(handler=cmd_defaults)


def _synced(path: Path) -> bool:
    from afc import cli  # late import: afc.cli imports this module

    return cli.icloud_synced(path)


def _parent() -> tuple[str | None, str | None]:
    """(first existing non-synced folder, or the one to offer creating when none exists)."""
    home = Path.home()
    for name in PARENT_FOLDERS:
        folder = home / name
        if folder.is_dir() and not _synced(folder):
            return str(folder), None
    suggested = home / SUGGESTED_FOLDER
    if suggested.exists() or _synced(suggested):
        return None, None
    return None, str(suggested)


def _git_global(key: str) -> str:
    try:
        result = subprocess.run(["git", "config", "--global", key], capture_output=True,
                                text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _identity() -> tuple[str, str, str]:
    """(name, email, source) from the latest project that has both, else git config, else none."""
    projects = load_registry(afc_home()).projects.values()
    for project in sorted(projects, key=lambda p: p.last_active, reverse=True):
        if project.git_name and project.git_email:
            return project.git_name, project.git_email, "projects"
    name, email = _git_global("user.name"), _git_global("user.email")
    if name and email:
        return name, email, "git-config"
    return "", "", "none"


def cmd_defaults(args: argparse.Namespace) -> dict:
    parent, suggest_create = _parent()
    name, email, source = _identity()
    return {"parent": parent, "suggest_create": suggest_create, "git_name": name,
            "git_email": email, "source": source, "ai_trailer": False}
