"""Locations and switches for Flight Control.

The workspace root defaults to ~/.A-FC and can be moved with AFC_HOME.
The A-FC repo itself never holds project data.
"""

import os
from pathlib import Path


def afc_home() -> Path:
    """Workspace root: $AFC_HOME if set, else ~/.A-FC. Need not exist."""
    override = os.environ.get("AFC_HOME")
    base = Path(override) if override else Path.home() / ".A-FC"
    return base.expanduser().resolve()


def afc_root() -> Path:
    """Root of the A-FC repo (the directory that contains the afc package)."""
    return Path(__file__).resolve().parent.parent


def maintain_enabled(home: Path) -> bool:
    """True when the maintain switch file exists under the workspace."""
    return (home / "maintain").exists()


def set_maintain(home: Path, on: bool) -> None:
    """Turn the maintain switch on (create file) or off (remove file)."""
    flag = home / "maintain"
    if on:
        home.mkdir(parents=True, exist_ok=True)
        flag.touch()
    else:
        flag.unlink(missing_ok=True)
