"""Which account add-ons may load in Flight Control sessions.

The allowed list lives in <root>/afc-addons.json. What is installed comes from
`claude plugin list --json`, run from the root so folder-level settings apply.
"""

import json
import shutil
import subprocess
from pathlib import Path

LIST_FILE = "afc-addons.json"


def allowed(root: Path) -> list[str]:
    """The add-on ids Flight Control sessions may use. A missing file means none."""
    path = Path(root) / LIST_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = data["allowed"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"{path} could not be read: {exc}") from exc
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise ValueError(f"{path}: 'allowed' must be a list of add-on names")
    return ids


def reported(root: Path) -> tuple[list[dict], str | None]:
    """(add-ons Claude Code reports, a plain note when they could not be read)."""
    if shutil.which("claude") is None:
        return [], "Claude Code (the claude command) isn't on the PATH, so add-ons weren't checked."
    try:
        done = subprocess.run(["claude", "plugin", "list", "--json"], cwd=str(root),
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return [], "Claude Code didn't answer when asked for its add-ons."
    try:
        data = json.loads(done.stdout)
    except ValueError:
        data = None
    if done.returncode != 0 or not isinstance(data, list):
        return [], "Claude Code gave an add-on list that couldn't be understood."
    return [d for d in data if isinstance(d, dict) and isinstance(d.get("id"), str)], None


def blocked(root: Path) -> tuple[list[str], str | None]:
    """(enabled add-ons not on the allowed list, a plain note when unknown)."""
    plugins, note = reported(root)
    ok = set(allowed(root))
    return [p["id"] for p in plugins if p.get("enabled") and p["id"] not in ok], note
