"""Per-project workspace folders under the workspace root (outside any repo)."""

import shutil
from pathlib import Path

from afc.config import afc_root
from afc.registry import validate_name

WORKSPACE_DIRS = ("plan", "resources", "reports", "skills", "drafts")


def create_workspace(home: Path, name: str) -> Path:
    """Create home/projects/<name>/ with its folders and plan templates.

    Existing files are never overwritten, so calling this again is safe.
    """
    validate_name(name)
    ws = home / "projects" / name
    for sub in WORKSPACE_DIRS:
        (ws / sub).mkdir(parents=True, exist_ok=True)
    templates = afc_root() / "templates" / "workspace" / "plan"
    for src in sorted(templates.glob("*.md")):
        dest = ws / "plan" / src.name
        if not dest.exists():
            shutil.copyfile(src, dest)
    return ws
