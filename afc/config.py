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
SEEN_AFTER = 30 * 86400  # a session ID's "seen" mark (sessions.d) is dropped after this
ASK_WITHIN = 12 * 3600  # a fork or clear is asked about when another session's flag is newer than this
# An unanswered question (maintain.d/<id>.ask) never lapses: only `maintain on|off` (the answer)
# ends it. The one cleanup is dropping an .ask older than SEEN_AFTER (_prune_asks), the age at which
# the ID counts as unseen again.


def valid_session(value: object) -> str | None:
    """The session ID when it is safe to use as a file name, else None."""
    return value if isinstance(value, str) and SESSION_ID.match(value) else None


# Conversation IDs from tools other than Claude Code (FC-054). Checked after Claude's own ID and
# AFC_SESSION so Claude Code behaviour is unchanged.
_TOOL_SESSION_ENV = ("CURSOR_CONVERSATION_ID",)


def current_session() -> str | None:
    """The session a command runs in: Claude Code's own ID, else the one the startup hook saved,
    else a tool conversation ID (Cursor). A plain fork no longer runs the hook's save, so
    AFC_SESSION can be the parent's; the live ID wins."""
    for name in ("CLAUDE_CODE_SESSION_ID", "AFC_SESSION", *_TOOL_SESSION_ENV):
        found = valid_session(os.environ.get(name, "").strip())
        if found:
            return found
    return None


def tool_session() -> str | None:
    """The non-Claude tool conversation ID when one is set (Cursor today), else None."""
    for name in _TOOL_SESSION_ENV:
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


def _branch_flag(home: Path) -> Path | None:
    """The switch for the branch this copy is on, used only when there is no session ID (Cursor,
    Codex, Copilot and other tools that give none). None when the branch can't be told."""
    from afc.update import _branch  # late import: update imports this module

    name = re.sub(r"[^A-Za-z0-9_-]", "_", _branch(afc_root()))[:100]
    return home / "maintain.branch.d" / name if name else None


def _branch_on(home: Path) -> bool:
    flag = _branch_flag(home)
    try:
        return bool(flag) and flag.exists() and time.time() - flag.stat().st_mtime < STALE_AFTER
    except OSError:
        return False


def maintain_scope(home: Path, session: str | None = None) -> str:
    """'session' (this session only), 'branch' (this copy's branch) or 'off'. A leftover global
    `maintain` file is ignored, and a copy on `main` is always off.

    Claude Code sessions never fall back to the branch switch (FC-036). A Cursor (or other tool)
    conversation ID with no session flag still honours an active branch switch, so `/afc mm` on
    the branch covers every Cursor chat's writes (FC-054)."""
    session = valid_session(session)
    if on_main():
        return "off"
    if session and (_flags(home) / session).exists():
        return "session"
    if session:
        # Tool chat whose ID matches this session: branch-wide /afc mm applies (FC-054).
        tool = tool_session()
        if tool and session == tool and _branch_on(home):
            return "branch"
        return "off"
    return "branch" if _branch_on(home) else "off"


def maintain_enabled(home: Path, session: str | None = None) -> bool:
    """True when maintenance mode is on for this session."""
    return maintain_scope(home, session) != "off"


NO_BRANCH = "Maintenance mode needs a branch name, and this copy isn't on a branch (detached HEAD)"


def undecided(home: Path, session: str | None = None) -> bool:
    """True while this session was asked "Flight Control or your project?" and hasn't answered
    (maintain.d/<id>.ask exists; it never lapses by time). A copy on `main` is never undecided."""
    session = valid_session(session)
    if not session or on_main():
        return False
    ask = _flags(home) / f"{session}.ask"
    try:
        return ask.exists()
    except OSError:
        return False


def set_maintain(home: Path, on: bool, session: str | None = None) -> None:
    """Turn maintenance mode on or off for one session; either answer ends "undecided" (removes
    the .ask file). With no usable session ID the switch belongs to this copy's branch instead; if the
    branch can't be told, turning it on raises ValueError. There is no global switch.

    A Cursor (or other tool) conversation ID uses the branch switch, not a per-chat flag, so
    `/afc mm` covers every chat on this copy's branch (FC-054)."""
    session = valid_session(session)
    flags = _flags(home)
    if on and on_main():
        raise ValueError(ON_MAIN)
    tool = tool_session()
    if session and tool and session == tool:
        # Tool chat: flip the branch switch; drop any leftover per-chat flag for this ID.
        try:
            (flags / session).unlink(missing_ok=True)
            (flags / f"{session}.ask").unlink(missing_ok=True)
        except OSError:
            pass
        session = None
    if not session:
        flag = _branch_flag(home)
        if on:
            if flag is None:
                raise ValueError(NO_BRANCH)
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.touch()
        elif flag is not None:
            flag.unlink(missing_ok=True)
        return
    if on:
        flags.mkdir(parents=True, exist_ok=True)
        (flags / session).touch()
        _prune(flags)
    elif session:
        (flags / session).unlink(missing_ok=True)
    if session:
        (flags / f"{session}.ask").unlink(missing_ok=True)


def _prune(flags: Path, age: float = STALE_AFTER) -> None:
    """Drop files older than `age`. Never touches .ask files: see _prune_asks."""
    cutoff = time.time() - age
    for flag in flags.iterdir():
        try:
            if flag.name.endswith(".ask"):
                continue
            if flag.stat().st_mtime < cutoff:
                flag.unlink()
        except OSError:
            pass


def _prune_asks(flags: Path) -> None:
    """Drop an unanswered question (.ask) older than SEEN_AFTER, the age at which its ID counts as
    unseen again (a flag older than ASK_WITHIN never asks). Nothing else ends one but an answer."""
    cutoff = time.time() - SEEN_AFTER
    for ask in flags.glob("*.ask"):
        try:
            if ask.stat().st_mtime < cutoff:
                ask.unlink()
        except OSError:
            pass


def seen(home: Path, session: str | None) -> bool:
    """Note that Flight Control has started this session ID, and say whether it already had.
    An ID that has ANY mark (sessions.d), maintenance flag or .ask file counts as seen, so a session
    that began before marks existed is not taken for new. Marks live in sessions.d and are pruned
    after SEEN_AFTER (30 days), longer than the maintenance flags. No usable ID counts as seen."""
    session = valid_session(session)
    if not session:
        return True
    folder = home / "sessions.d"
    try:
        mark = folder / session
        flags = _flags(home)
        if flags.is_dir():
            _prune_asks(flags)
        existed = mark.exists() or (flags / session).exists() or (flags / f"{session}.ask").exists()
        folder.mkdir(parents=True, exist_ok=True)
        mark.touch()
        _prune(folder, SEEN_AFTER)
        return existed
    except OSError:
        return True  # never ask because of a file problem


def needs_choice(home: Path, session: str | None, source: object, was_seen: bool,
                 now: float | None = None) -> bool:
    """True when this start is a fork or clear: source resume, fork or clear, an ID not seen before
    (`was_seen` is what `seen` returned), no flag for this session, and another session's flag
    under ASK_WITHIN old. Then maintain.d/<id>.ask is written: undecided until `maintain on` or
    `maintain off`. Never raises."""
    session = valid_session(session)
    if not session or was_seen or source not in ("resume", "fork", "clear"):
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
