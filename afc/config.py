"""Locations and switches for Flight Control.

The workspace root defaults to ~/.A-FC and can be moved with AFC_HOME.
The A-FC repo itself never holds project data.
"""

import os
import re
import time
from pathlib import Path


def afc_home() -> Path:
    """Workspace root: $AFC_HOME if set, else ~/.A-FC. Need not exist."""
    override = os.environ.get("AFC_HOME")
    base = Path(override) if override else Path.home() / ".A-FC"
    return base.expanduser().resolve()


def afc_root() -> Path:
    """Root of the A-FC repo (the directory that contains the afc package)."""
    return Path(__file__).resolve().parent.parent


SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
STALE_AFTER = 7 * 86400  # a session's maintenance flag older than this is dropped


def valid_session(value: object) -> str | None:
    """The session ID when it is safe to use as a file name, else None."""
    return value if isinstance(value, str) and SESSION_ID.match(value) else None


def current_session() -> str | None:
    """The session a command runs in: the ID the startup hook saved, else Claude Code's own."""
    for name in ("AFC_SESSION", "CLAUDE_CODE_SESSION_ID"):
        found = valid_session(os.environ.get(name, "").strip())
        if found:
            return found
    return None


def _flags(home: Path) -> Path:
    return home / "maintain.d"


def maintain_scope(home: Path, session: str | None = None) -> str:
    """'global' (one switch for every session), 'session' (this session only) or 'off'."""
    if (home / "maintain").exists():
        return "global"
    session = valid_session(session)
    return "session" if session and (_flags(home) / session).exists() else "off"


def maintain_enabled(home: Path, session: str | None = None) -> bool:
    """True when maintenance mode is on for this session."""
    return maintain_scope(home, session) != "off"


def set_maintain(home: Path, on: bool, session: str | None = None) -> None:
    """Turn maintenance mode on or off for one session. With no usable session ID it falls back
    to the single global switch. Turning off also clears the global switch."""
    session = valid_session(session)
    flags = _flags(home)
    if on and session:
        flags.mkdir(parents=True, exist_ok=True)
        (flags / session).touch()
        _prune(flags)
    elif on:
        home.mkdir(parents=True, exist_ok=True)
        (home / "maintain").touch()
    else:
        (home / "maintain").unlink(missing_ok=True)
        if session:
            (flags / session).unlink(missing_ok=True)


def _prune(flags: Path) -> None:
    cutoff = time.time() - STALE_AFTER
    for flag in flags.iterdir():
        try:
            if flag.stat().st_mtime < cutoff:
                flag.unlink()
        except OSError:
            pass
