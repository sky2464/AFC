"""Swap the active project's own skills and MCP servers into the A-FC folder.

Skills are linked into <root>/.claude/skills/project-<name>/ (git-ignored). Servers go into
<root>/.mcp.json (git-ignored); the names Flight Control wrote are tracked in the local settings
file (afcManagedMcp) and pre-approved through enabledMcpjsonServers, so a server the user added by
hand is never touched. Only env_keys are stored: values never reach any file.
"""

import json
import re
import shutil
from pathlib import Path

from afc.secrets import find_secrets
from afc.session_dirs import _atomic_write, _read_settings, settings_path

MANAGED_KEY = "afcManagedMcp"
ENABLED_KEY = "enabledMcpjsonServers"
PREFIX = "project-"
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_VAR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ENTRY_KEYS = {"command", "args", "env_keys", "description"}


class ToolsError(Exception):
    """The project's tools could not be swapped; nothing was changed."""


def _skills_dir(root: Path) -> Path:
    return Path(root) / ".claude" / "skills"


def _mcp_path(root: Path) -> Path:
    return Path(root) / ".mcp.json"


def project_servers(ws: Path) -> dict:
    """The servers from <ws>/mcp.json as Claude Code entries. Raises ToolsError if unsafe."""
    path = Path(ws) / "mcp.json"
    if not path.exists():
        return {}
    try:
        servers = json.loads(path.read_text(encoding="utf-8"))["servers"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ToolsError(f"{path} could not be read: {exc}") from exc
    if not isinstance(servers, dict):
        raise ToolsError(f"{path}: 'servers' must hold named servers")
    return {name: _entry(path, name, entry) for name, entry in servers.items()}


def _entry(path: Path, name: str, entry) -> dict:
    if not _NAME.match(str(name)):
        raise ToolsError(f"{path}: the server name '{name}' isn't a plain name")
    if not isinstance(entry, dict) or not isinstance(entry.get("command"), str):
        raise ToolsError(f"{path}: server '{name}' needs a command")
    extra = set(entry) - _ENTRY_KEYS
    if extra:
        hint = " Keep secrets out of files: list only the variable names in env_keys." if "env" in extra else ""
        raise ToolsError(f"{path}: server '{name}' has unexpected setting(s) {', '.join(sorted(extra))}.{hint}")
    args = entry.get("args", [])
    keys = entry.get("env_keys", [])
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise ToolsError(f"{path}: server '{name}': args must be a list of text")
    if not isinstance(keys, list) or not all(isinstance(k, str) and _VAR.match(k) for k in keys):
        raise ToolsError(f"{path}: server '{name}': env_keys must be variable names, not values")
    for text in [entry["command"], *args, json.dumps(entry, indent=2)]:
        if find_secrets(text):
            raise ToolsError(f"{path}: server '{name}' has what looks like a real secret. "
                             "Keep secrets out of files: list only the variable name in env_keys.")
    out: dict = {"command": entry["command"], "args": args}
    if keys:
        out["env"] = {k: "${" + k + "}" for k in keys}
    return out


def project_skills(ws: Path) -> dict[str, Path]:
    """{link name: skill folder} for each skill folder holding a SKILL.md."""
    base = Path(ws) / "skills"
    if not base.is_dir():
        return {}
    return {PREFIX + d.name: d.resolve() for d in sorted(base.iterdir())
            if d.is_dir() and _NAME.match(d.name) and (d / "SKILL.md").is_file()}


def _linked(root: Path) -> dict[str, str]:
    """{name: where it points ('' for a copied folder)} for every project-* skill entry."""
    base = _skills_dir(root)
    if not base.is_dir():
        return {}
    return {p.name: (str(p.resolve()) if p.is_symlink() else "") for p in sorted(base.glob(PREFIX + "*"))}


def _mcp_data(root: Path) -> dict:
    path = _mcp_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ToolsError(f"{path} could not be read: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
        raise ToolsError(f"{path} must hold a JSON object with 'mcpServers'")
    return data


def _managed(settings: dict) -> list[str]:
    old = settings.get(MANAGED_KEY, [])
    return [n for n in old if isinstance(n, str)] if isinstance(old, list) else []


def swap_in(root: Path, ws: Path) -> None:
    """Make exactly this project's skills and servers the managed ones. Validates before writing."""
    root = Path(root)
    skills = project_skills(ws)
    servers = project_servers(ws)
    data = _mcp_data(root)
    settings = _read_settings(settings_path(root))
    old = _managed(settings)
    live = data.get("mcpServers", {})
    for name in servers:
        if name in live and name not in old:
            raise ToolsError(f"A server named '{name}' is already set up by hand in {_mcp_path(root)}; "
                             "rename the project's server.")
    _write_skills(root, skills)
    _write_servers(root, data, settings, old, servers)


def clear(root: Path) -> None:
    """Remove every project skill link and every server Flight Control wrote."""
    root = Path(root)
    data = _mcp_data(root)
    settings = _read_settings(settings_path(root))
    _write_skills(root, {})
    _write_servers(root, data, settings, _managed(settings), {})


def _write_skills(root: Path, skills: dict[str, Path]) -> None:
    base = _skills_dir(root)
    for name in _linked(root):
        _remove(base / name)
    if not skills:
        return
    base.mkdir(parents=True, exist_ok=True)
    for name, target in skills.items():
        try:
            (base / name).symlink_to(target, target_is_directory=True)
        except OSError:
            shutil.copytree(target, base / name)  # a link can't be made here: copy instead


def _write_servers(root: Path, data: dict, settings: dict, old: list[str], servers: dict) -> None:
    mine = {k: v for k, v in data.get("mcpServers", {}).items() if k not in old}
    mine.update(servers)
    data = {k: v for k, v in data.items() if k != "mcpServers"}
    if mine:
        data["mcpServers"] = mine
    path = _mcp_path(root)
    if data:
        _atomic_write(path, json.dumps(data, indent=2) + "\n")
    else:
        path.unlink(missing_ok=True)
    enabled = settings.get(ENABLED_KEY, [])
    enabled = [e for e in enabled if e not in old] if isinstance(enabled, list) else []
    enabled += [n for n in servers if n not in enabled]
    for key, value in ((ENABLED_KEY, enabled), (MANAGED_KEY, list(servers))):
        if value:
            settings[key] = value
        else:
            settings.pop(key, None)
    _atomic_write(settings_path(root), json.dumps(settings, indent=2) + "\n")


def mismatches(root: Path, ws: Path | None) -> list[str]:
    """Plain lines for what is loaded but not the active project's (ws None = no active project)."""
    root = Path(root)
    skills = project_skills(ws) if ws else {}
    servers = project_servers(ws) if ws else {}
    found: list[str] = []
    have = _linked(root)
    for name, target in skills.items():
        if name not in have:
            found.append(f"The project skill {name[len(PREFIX):]} isn't loaded.")
        elif have[name] and have[name] != str(target):
            found.append(f"The project skill {name[len(PREFIX):]} points at the wrong folder.")
    found += [f"The skill {n[len(PREFIX):]} belongs to another project." for n in have if n not in skills]
    managed = _managed(_read_settings(settings_path(root)))
    live = _mcp_data(root).get("mcpServers", {})
    for name, entry in servers.items():
        if live.get(name) != entry or name not in managed:
            found.append(f"The project server {name} isn't set up as the project says.")
    found += [f"The server {n} belongs to another project." for n in managed if n not in servers]
    return found


def snapshot(root: Path):
    """Return a function that puts the skill links and .mcp.json back as they are now."""
    root = Path(root)
    mcp = _mcp_path(root)
    before = mcp.read_bytes() if mcp.exists() else None
    targets = {n: (Path(t) if t else None) for n, t in _linked(root).items()}

    def restore() -> None:
        if before is None:
            mcp.unlink(missing_ok=True)
        else:
            mcp.write_bytes(before)
        base = _skills_dir(root)
        for name in _linked(root):
            _remove(base / name)
        for name, target in targets.items():
            if target is not None:
                base.mkdir(parents=True, exist_ok=True)
                (base / name).symlink_to(target, target_is_directory=True)

    return restore


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
