"""Per-project connector list: which account connectors (Gmail, Notion, GitHub...) a project uses.

The list lives in the project's workspace (connectors.json), never in the app's code folder.
Two kinds of entries: "found" (read from what the project shows, through the small fixed map in
afc-connectors.json) and "named" (the user asked for it). Nothing is guessed beyond the map.
"""

import json
import os
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
