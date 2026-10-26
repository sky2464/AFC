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
ASK_WITHIN = 12 * 3600  # a fork or clear is asked about when another session's flag is newer than this


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


ON_MAIN = "Flight Control is changed in the developer copy on dev, not here"


def on_main() -> bool:
    """True when this copy of Flight Control is on the `main` branch (the daily folder)."""
    from afc.update import _branch  # late import: update imports this module

    return _branch(afc_root()) == "main"


def maintain_scope(home: Path, session: str | None = None) -> str:
    """'session' (this session only) or 'off'. A leftover global `maintain` file is ignored, and
    a copy on `main` is always off."""
    session = valid_session(session)
    if on_main():
        return "off"
    return "session" if session and (_flags(home) / session).exists() else "off"


def maintain_enabled(home: Path, session: str | None = None) -> bool:
    """True when maintenance mode is on for this session."""
    return maintain_scope(home, session) != "off"


NO_SESSION = ("Maintenance mode needs this session's ID; open Flight Control in Claude Code "
              "and try again")


def undecided(home: Path, session: str | None = None) -> bool:
    """True while this session was asked "Flight Control or your project?" and hasn't answered
    (maintain.d/<id>.ask exists). A copy on `main` is never undecided."""
    session = valid_session(session)
    return bool(session) and not on_main() and (_flags(home) / f"{session}.ask").exists()


def set_maintain(home: Path, on: bool, session: str | None = None) -> None:
    """Turn maintenance mode on or off for one session; either answer ends "undecided" (removes
    the .ask file). Turning it on with no usable session ID raises ValueError; there is no
    global switch."""
    session = valid_session(session)
    flags = _flags(home)
    if on and on_main():
        raise ValueError(ON_MAIN)
    if on:
        if not session:
            raise ValueError(NO_SESSION)
        flags.mkdir(parents=True, exist_ok=True)
        (flags / session).touch()
        _prune(flags)
    elif session:
        (flags / session).unlink(missing_ok=True)
    if session:
        (flags / f"{session}.ask").unlink(missing_ok=True)


def _prune(flags: Path) -> None:
    cutoff = time.time() - STALE_AFTER
    for flag in flags.iterdir():
        try:
            if flag.stat().st_mtime < cutoff:
                flag.unlink()
        except OSError:
            pass


def seen(home: Path, session: str | None) -> bool:
    """Note that Flight Control has started this session ID, and say whether it already had.
    Records live in sessions.d and are pruned like the maintenance flags. No usable ID counts as seen."""
    session = valid_session(session)
    if not session:
        return True
    folder = home / "sessions.d"
    try:
        mark = folder / session
        existed = mark.exists()
        folder.mkdir(parents=True, exist_ok=True)
        mark.touch()
        _prune(folder)
        return existed
    except OSError:
        return True  # never ask because of a file problem


def needs_choice(home: Path, session: str | None, source: object, was_seen: bool,
                 now: float | None = None) -> bool:
    """True when this start is a fork or clear: source resume or clear, an ID not seen before
    (`was_seen` is what `seen` returned), no flag for this session, and another session's flag
    under ASK_WITHIN old. Then maintain.d/<id>.ask is written: undecided until `maintain on` or
    `maintain off`. Never raises."""
    session = valid_session(session)
    if not session or was_seen or source not in ("resume", "clear"):
        return False
    try:
        if on_main():
            return False
        flags = _flags(home)
        if (flags / session).exists():
            return False
        now = time.time() if now is None else now
        recent = any(
            flag.name != session and valid_session(flag.name) and now - flag.stat().st_mtime < ASK_WITHIN
            for flag in flags.iterdir() if flag.is_file()
        )
        if not recent:
            return False
        (flags / f"{session}.ask").touch()
        return True
    except OSError:
        return False
