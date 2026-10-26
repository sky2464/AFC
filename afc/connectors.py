"""Per-project connector list: which account connectors (Gmail, Notion, GitHub...) a project uses.

The list lives in the project's workspace (connectors.json), never in the app's code folder.
Two kinds of entries: "found" (read from what the project shows, through the small fixed map in
afc-connectors.json) and "named" (the user asked for it). Nothing is guessed beyond the map.
"""

import json
import os
import re
from pathlib import Path

from afc import git_ops
from afc.config import afc_root

FILE = "connectors.json"
_SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def fact_map() -> dict[str, str]:
    try:
        data = json.loads((afc_root() / "afc-connectors.json").read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data["facts"].items()}
    except (OSError, ValueError, KeyError, AttributeError):
        return {}


def _has_file(code: Path, suffixes: tuple[str, ...], limit: int = 2000) -> bool:
    seen = 0
    for root, dirs, files in os.walk(code):
        dirs[:] = [d for d in dirs if d not in _SKIP]
        for f in files:
            seen += 1
            if f.lower().endswith(suffixes):
                return True
            if seen >= limit:
                return False
    return False


def facts_of(code: Path) -> set[str]:
    """What the project shows, as fact names used in afc-connectors.json."""
    found: set[str] = set()
    if not code.is_dir():
        return found
    if "github.com" in git_ops.remote_url(code):
        found.add("github_remote")
    if _has_file(code, (".fig", ".figma")):
        found.add("figma_files")
    if (code / "vercel.json").exists():
        found.add("vercel_config")
    if (code / "netlify.toml").exists():
        found.add("netlify_config")
    return found


def detect(code: Path) -> list[str]:
    mapping = fact_map()
    return sorted({mapping[f] for f in facts_of(code) if f in mapping})


def tracked_names(root: Path | None = None) -> list[str]:
    """The connector names the tracked .claude/settings.json holds back from the first start
    (the 'tracked_deny' list in afc-connectors.json)."""
    try:
        data = json.loads(((root or afc_root()) / "afc-connectors.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    found = data.get("tracked_deny") if isinstance(data, dict) else None
    return [n for n in found if isinstance(n, str)] if isinstance(found, list) else []


def tracked_in_settings(root: Path | None = None) -> list[str]:
    """The names in the tracked .claude/settings.json deniedMcpServers (read only)."""
    try:
        data = json.loads(((root or afc_root()) / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    found = data.get(DENIED_KEY) if isinstance(data, dict) else None
    return [n for n in (_entry_name(e) for e in found) if n] if isinstance(found, list) else []


def _clean(name: str) -> str:
    name = " ".join(name.split())
    if name.lower().startswith("claude.ai "):
        name = name[len("claude.ai "):].strip()
    return name


def load(workspace: Path) -> dict:
    try:
        data = json.loads((workspace / FILE).read_text(encoding="utf-8"))
        return {"found": list(data.get("found", [])), "named": list(data.get("named", []))}
    except (OSError, ValueError, AttributeError):
        return {"found": [], "named": []}


def _save(workspace: Path, data: dict) -> None:
    path = workspace / FILE
    tmp = path.with_name(FILE + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def names(data: dict) -> list[str]:
    out: list[str] = []
    for n in data["named"] + data["found"]:
        if n.lower() not in {o.lower() for o in out}:
            out.append(n)
    return out


def refresh(workspace: Path, code: Path) -> dict:
    """Fill the found part from what the project shows; keep what the user named."""
    data = load(workspace)
    found = detect(code)
    if found != data["found"]:
        data["found"] = found
        _save(workspace, data)
    return data


def add(workspace: Path, name: str) -> tuple[dict, bool]:
    """Add a connector by name. Returns the data and whether it was new."""
    name = _clean(name)
    data = load(workspace)
    if not name:
        raise ValueError("Say which connector to add, for example Gmail.")
    if name.lower() in {n.lower() for n in names(data)}:
        return data, False
    data["named"].append(name)
    _save(workspace, data)
    return data, True


# ---- holding the rest back at session start (FC-034 slice 3)

DENIED_KEY = "deniedMcpServers"
HELD_KEY = "afcBlockedConnectors"  # connector names Flight Control blocked (the user's own entries stay)
PREFIX = "claude.ai "


def known(root: Path | None = None) -> list[str]:
    """The account connectors this session reports at start, as full names ('claude.ai Gmail'),
    read from `claude mcp list`. Empty when it can't be read: then nothing is blocked."""
    import subprocess

    try:
        out = subprocess.run(["claude", "mcp", "list"], cwd=str(root) if root else None,
                             capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    found: list[str] = []
    for line in out.stdout.splitlines():
        m = re.match(r"^(claude\.ai [^:]+?):\s", line)
        if m and m.group(1) not in found:
            found.append(m.group(1))
    return found


def _user_set(root: Path, key: str, claude_json: Path | None = None) -> set[str]:
    path = claude_json or (Path.home() / ".claude.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        vals = data["projects"][str(root)][key]
        return {n for n in vals if isinstance(n, str)}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def user_off(root: Path, claude_json: Path | None = None) -> set[str]:
    """Connectors the user switched off in /mcp for this folder; left alone."""
    return _user_set(root, "disabledMcpServers", claude_json)


def user_on(root: Path, claude_json: Path | None = None) -> set[str]:
    """Connectors the user switched on in /mcp for this folder; never blocked."""
    return _user_set(root, "enabledMcpServers", claude_json)


def held_now(root: Path) -> list[str]:
    """Connectors Flight Control already blocks here; a blocked connector no longer shows in the
    session's report, so it stays a candidate."""
    from afc.session_dirs import _read_settings, settings_path

    mine = _read_settings(settings_path(root)).get(HELD_KEY, [])
    return [n for n in mine if isinstance(n, str)] if isinstance(mine, list) else []


def to_hold(listed: list[str], root: Path, claude_json: Path | None = None) -> list[str]:
    """Connectors to block: reported by the session (or already held), not on the project's list,
    not switched on or off by the user in /mcp."""
    keep = {n.lower() for n in listed}
    skip = user_off(root, claude_json) | user_on(root, claude_json)
    skip |= {PREFIX + _clean(n) for n in skip}
    seen = known(root)
    out = []
    for n in dict.fromkeys(seen + held_now(root)):
        if n[len(PREFIX):].lower() in keep or n in skip or n[len(PREFIX):] in skip:
            continue
        out.append(n)
    return out


def _entry_name(entry) -> str | None:
    if isinstance(entry, dict) and isinstance(entry.get("serverName"), str):
        return entry["serverName"]
    return entry if isinstance(entry, str) else None


def hold(root: Path, names_: list[str]) -> int:
    """Block exactly these connectors here (deniedMcpServers) and return how many were newly held.
    Names Flight Control held earlier that are not in the list come back; entries the user wrote
    and all other keys are kept. Writes only when something changes."""
    from afc.session_dirs import GrantError, _atomic_write, _read_settings, settings_path

    path = settings_path(root)
    settings = _read_settings(path)
    denied = settings.get(DENIED_KEY, [])
    if not isinstance(denied, list):
        raise GrantError(f"{path}: '{DENIED_KEY}' must be a list")
    mine = settings.get(HELD_KEY, [])
    mine = [n for n in mine if isinstance(n, str)] if isinstance(mine, list) else []
    wanted = list(dict.fromkeys(names_))
    present = {_entry_name(e) for e in denied}
    new = [n for n in wanted if n not in present]
    kept = [e for e in denied if not (_entry_name(e) in mine and _entry_name(e) not in wanted)]
    held = [n for n in wanted if n in present and n not in mine]  # the user's own entry: not ours
    final = kept + [{"serverName": n} for n in new]
    mine_now = [n for n in wanted if n not in held]
    if final == denied and mine_now == mine:
        return 0
    if final:
        settings[DENIED_KEY] = final
    else:
        settings.pop(DENIED_KEY, None)
    if mine_now:
        settings[HELD_KEY] = mine_now
    else:
        settings.pop(HELD_KEY, None)
    _atomic_write(path, json.dumps(settings, indent=2) + "\n")
    return len([n for n in new if n not in mine])


def hold_for(root: Path, workspace: Path, code: Path) -> tuple[int, int]:
    """Hold back every connector not on the project's list. Returns (newly held, held in all).
    On any error the settings file is put back as it was and the error is raised."""
    from afc.session_dirs import check_settings, settings_path
    from afc.undo import Undo

    check_settings(root)
    wanted = to_hold(names(refresh(workspace, code)), root)
    undo = Undo(settings_path(root))
    undo.save_settings()
    try:
        return hold(root, wanted), len(wanted)
    except BaseException:
        undo.rollback()
        raise


def hold_for_workspace(root: Path, home: Path) -> tuple[int, int]:
    """With no active project: hold back every connector not on the workspace's own list
    (connectors.json in the workspace root; missing means empty). Same undo as hold_for."""
    from afc.session_dirs import check_settings, settings_path
    from afc.undo import Undo

    check_settings(root)
    wanted = to_hold(names(load(home)), root)
    undo = Undo(settings_path(root))
    undo.save_settings()
    try:
        return hold(root, wanted), len(wanted)
    except BaseException:
        undo.rollback()
        raise


def release(root: Path, name: str) -> bool:
    """Unblock one connector Flight Control held here, so it loads from the next start. Only
    entries Flight Control wrote are removed; the user's own entries and choices stay."""
    from afc.session_dirs import _atomic_write, _read_settings, settings_path

    full = PREFIX + _clean(name)
    path = settings_path(root)
    settings = _read_settings(path)
    mine = settings.get(HELD_KEY, [])
    mine = [n for n in mine if isinstance(n, str)] if isinstance(mine, list) else []
    hit = [n for n in mine if n.lower() == full.lower()]
    if not hit:
        return release_tracked(root, full)
    denied = settings.get(DENIED_KEY, [])
    denied = denied if isinstance(denied, list) else []
    left = [e for e in denied if _entry_name(e) not in hit]
    rest = [n for n in mine if n not in hit]
    for key, val in ((DENIED_KEY, left), (HELD_KEY, rest)):
        if val:
            settings[key] = val
        else:
            settings.pop(key, None)
    _atomic_write(path, json.dumps(settings, indent=2) + "\n")
    return True


def release_tracked(root: Path, full: str) -> bool:
    """Take one name out of the tracked .claude/settings.json deniedMcpServers (FC-038 slice 3) and
    hide that edit from git with skip-worktree, so `git status` stays clean and updates are not
    refused. Only that name is removed; every other key stays. Put back as it was on any error."""
    import subprocess

    from afc.session_dirs import _atomic_write

    path = root / ".claude" / "settings.json"
    try:
        old = path.read_text(encoding="utf-8")
        settings = json.loads(old)
    except (OSError, ValueError):
        return False
    denied = settings.get(DENIED_KEY) if isinstance(settings, dict) else None
    if not isinstance(denied, list):
        return False
    left = [e for e in denied if (_entry_name(e) or "").lower() != full.lower()]
    if len(left) == len(denied):
        return False
    if left:
        settings[DENIED_KEY] = left
    else:
        settings.pop(DENIED_KEY, None)
    _atomic_write(path, json.dumps(settings, indent=1) + "\n")
    try:
        subprocess.run(["git", "-C", str(root), "update-index", "--skip-worktree",
                        ".claude/settings.json"], check=True, capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        _atomic_write(path, old)
        raise
    return True
