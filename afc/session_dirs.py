"""Grant the active project's code folder to Claude Code sessions.

Writes permissions.additionalDirectories into <root>/.claude/settings.local.json,
the per-machine settings file that the A-FC repo ignores.
"""

import json
import os
from pathlib import Path


class GrantError(Exception):
    """The settings file exists but cannot be merged safely, so it was left alone."""


def grant_dirs(root: Path, dirs: list[Path]) -> list[str]:
    """Add the resolved dirs to additionalDirectories and return the full list.

    Other keys are kept. Existing entries keep their order, and duplicates are dropped.
    """
    path = root / ".claude" / "settings.local.json"
    settings = _read_settings(path)
    permissions = settings.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        raise GrantError(f"{path}: 'permissions' must be a JSON object")
    current = permissions.get("additionalDirectories", [])
    if not isinstance(current, list):
        raise GrantError(f"{path}: 'permissions.additionalDirectories' must be a list")

    merged: list[str] = []
    for entry in [*current, *(str(Path(d).resolve()) for d in dirs)]:
        if entry not in merged:
            merged.append(entry)
    permissions["additionalDirectories"] = merged
    _atomic_write(path, json.dumps(settings, indent=2) + "\n")
    return merged


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
