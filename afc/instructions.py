"""The instruction file other AI tools read: AGENTS.md, generated from CLAUDE.md (FC-051).

Cursor, Codex and Antigravity read AGENTS.md on their own; GitHub Copilot is pointed at it by
.github/copilot-instructions.md. CLAUDE.md stays the one file a person edits.
"""

from pathlib import Path

NOTICE = "<!-- Generated from CLAUDE.md by `sh bin/afc instructions --write`. Edit CLAUDE.md, not this file. -->"

PREFACE = """\
# Flight Control, for AI tools other than Claude Code

The rules below were written for Claude Code. In any other tool, read them like this:

- **"Skills"** are plain instruction files in `.claude/skills/<name>/SKILL.md`. When the table says to
  use one, open and follow it.
- **`/afc`** is a command file, `.claude/commands/afc.md`. In a tool without slash commands, when the
  user says `afc`, follow that file.
- **Your tool may have no safety hooks.** Before a risky shell command or a file write, ask Flight
  Control: `sh bin/afc guard --shell "<command>"` or `sh bin/afc guard --write <path>`. Exit code 2
  means blocked: read the reason, do not work around it.
- **Maintenance mode** (changing Flight Control itself) needs no Claude Code session. Run
  `sh bin/afc maintain status`; if it is off and the user wants Flight Control changed, tell them
  and offer `sh bin/afc maintain on`. Never on `main`.
- **Commits** are checked for secrets by `.githooks/pre-commit`
  (`git config core.hooksPath .githooks` turns it on) and in CI.

---

"""

COPILOT = """\
# Flight Control

Follow the rules in [AGENTS.md](../AGENTS.md) at the root of this repository. It is generated from
CLAUDE.md; do not copy its rules here.
"""


def render(root: Path) -> str:
    claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
    return f"{NOTICE}\n\n{PREFACE}{claude}"


def targets(root: Path) -> dict[Path, str]:
    """Every generated file and what it should hold."""
    return {root / "AGENTS.md": render(root), root / ".github" / "copilot-instructions.md": COPILOT}


def out_of_date(root: Path) -> list[Path]:
    stale = []
    for path, text in targets(root).items():
        try:
            same = path.read_text(encoding="utf-8") == text
        except OSError:
            same = False
        if not same:
            stale.append(path)
    return stale


def write(root: Path) -> list[Path]:
    changed = out_of_date(root)
    for path, text in targets(root).items():
        if path in changed:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    return changed
