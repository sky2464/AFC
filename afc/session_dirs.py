"""Grant the active project's code folder to Claude Code sessions.

Writes permissions.additionalDirectories into <root>/.claude/settings.local.json,
the per-machine settings file that the A-FC repo ignores.
"""

import json
import os
from pathlib import Path


GRANTED_KEY = "afcGranted"  # entries of additionalDirectories that Flight Control added


class GrantError(Exception):
    """The settings file exists but cannot be merged safely, so it was left alone."""


def settings_path(root: Path) -> Path:
    return root / ".claude" / "settings.local.json"


def check_settings(root: Path) -> None:
    """Raise GrantError if the settings file cannot be merged. Writes nothing."""
    path = settings_path(root)
    _current_dirs(_read_settings(path), path)


def grant_dirs(root: Path, dirs: list[Path]) -> list[str]:
    """Grant the resolved dirs in additionalDirectories and return the full list.

    Entries Flight Control granted earlier (tracked in the sibling key GRANTED_KEY) are
    replaced, so only the latest dirs stay granted. Entries the user added are kept in
    order; other keys are kept; duplicates are dropped.
    """
    path = settings_path(root)
    settings = _read_settings(path)
    current = _current_dirs(settings, path)
    previous = settings.get(GRANTED_KEY, [])
    if not isinstance(previous, list):
        raise GrantError(f"{path}: '{GRANTED_KEY}' must be a list")
    user = [e for e in current if e not in previous]
    wanted = [str(Path(d).resolve()) for d in dirs]

    merged: list[str] = []
    for entry in [*user, *wanted]:
        if entry not in merged:
            merged.append(entry)
    settings.setdefault("permissions", {})["additionalDirectories"] = merged
    settings[GRANTED_KEY] = [d for d in dict.fromkeys(wanted) if d not in user]
    _atomic_write(path, json.dumps(settings, indent=2) + "\n")
    return merged


def granted_now(root: Path) -> tuple[list[str], list[str]]:
    """(every entry in additionalDirectories, the ones Flight Control added). Writes nothing."""
    path = settings_path(root)
    settings = _read_settings(path)
    previous = settings.get(GRANTED_KEY, [])
    return _current_dirs(settings, path), previous if isinstance(previous, list) else []


def drop_dirs(root: Path, gone: list[str]) -> None:
    """Remove these entries from additionalDirectories and from Flight Control's own list."""
    path = settings_path(root)
    settings = _read_settings(path)
    current = _current_dirs(settings, path)
    settings.setdefault("permissions", {})["additionalDirectories"] = [e for e in current if e not in gone]
    if isinstance(settings.get(GRANTED_KEY), list):
        settings[GRANTED_KEY] = [e for e in settings[GRANTED_KEY] if e not in gone]
    _atomic_write(path, json.dumps(settings, indent=2) + "\n")


def _current_dirs(settings: dict, path: Path) -> list:
    permissions = settings.get("permissions", {})
    if not isinstance(permissions, dict):
        raise GrantError(f"{path}: 'permissions' must be a JSON object")
    current = permissions.get("additionalDirectories", [])
    if not isinstance(current, list):
        raise GrantError(f"{path}: 'permissions.additionalDirectories' must be a list")
    return current


def _read_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GrantError(f"{path} could not be read: {exc}") from exc
    if not isinstance(data, dict):
        raise GrantError(f"{path} must hold a JSON object")
    return data


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
