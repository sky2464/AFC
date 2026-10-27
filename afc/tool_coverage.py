"""Which AI tools Flight Control protects, for `sh bin/afc check` (FC-051).

Per tool: whether it gets the instructions, a hook that asks the guard before an action, and the
commit check. Reads files only; the one git call is the setting that turns the commit check on.
"""

import subprocess
from pathlib import Path

from afc import instructions

TOOLS = {
    "cursor": ("Cursor", "AGENTS.md", ".cursor/hooks.json", "shell commands and file reads, not edits"),
    "codex": ("Codex", "AGENTS.md", ".codex/hooks.json", "shell commands and edits; you trust it once with /hooks"),
    "copilot": ("GitHub Copilot", ".github/copilot-instructions.md", ".github/hooks/flight-control.json",
                "shell commands and edits; in preview in VS Code"),
    "antigravity": ("Antigravity", "AGENTS.md", ".agents/hooks.json", "shell commands and edits"),
}


def _commit_check(root: Path) -> str:
    if not (root / ".githooks" / "pre-commit").exists():
        return "missing"
    try:
        done = subprocess.run(["git", "config", "core.hooksPath"], cwd=root, capture_output=True, text=True,
                              timeout=5, stdin=subprocess.DEVNULL)
        path = done.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return "on" if path.rstrip("/") == ".githooks" else "off"


def coverage(root: Path) -> list[dict]:
    stale = {p.relative_to(root).as_posix() for p in instructions.out_of_date(root)}
    commit = _commit_check(root)
    found = []
    for key, (name, instruction_file, hook_file, blocks) in TOOLS.items():
        hook = root / hook_file
        found.append({
            "tool": name,
            "instructions": ("missing" if not (root / instruction_file).exists()
                             else "out of date" if instruction_file in stale else "ok"),
            "hooks": "ok" if hook.exists() and f"hook adapter {key}" in hook.read_text(encoding="utf-8") else "missing",
            "hooks_block": blocks,
            "commit_check": commit,
        })
    return found


def lines(found: list[dict]) -> list[str]:
    """One plain line per tool, then one line on turning the commit check on if it is off."""
    out = []
    for item in found:
        commit = {"on": "on", "off": "off", "missing": "missing"}.get(item["commit_check"], "unknown")
        out.append(f"{item['tool']}: instructions {item['instructions']}, hook {item['hooks']}"
                   f" (it can block {item['hooks_block']}), commit check {commit}")
    if any(item["commit_check"] == "off" for item in found):
        out.append("To turn the commit check on, run once in this folder: git config core.hooksPath .githooks")
    return out
