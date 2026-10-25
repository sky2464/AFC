"""Short form of the rule modules: each rules/<name>.md keeps its Do and Never sections in
rules/short/<name>.md, which `sh bin/afc modules` hands out by default. The long file stays the
only place a rule is edited; regenerate the short ones with `python3 -m afc.rules`.
"""

import re
from pathlib import Path

from afc.config import afc_root

KEEP = ("Do", "Never")


def short_form(text: str) -> str:
    """The title plus the Do and Never sections of a rule module, in that order."""
    parts = re.split(r"^(?=## )", text, flags=re.M)
    sections = {p.splitlines()[0][3:].strip(): p.rstrip("\n") for p in parts[1:]}
    missing = [name for name in KEEP if name not in sections]
    if missing:
        raise ValueError(f"rule module has no {' or '.join(missing)} section")
    return "\n\n".join([parts[0].rstrip("\n"), *(sections[name] for name in KEEP)]) + "\n"


def write_short(root: Path) -> list[Path]:
    """Write rules/short/<name>.md for every rule under root; drop short files with no rule."""
    rules = root / "rules"
    short = rules / "short"
    short.mkdir(parents=True, exist_ok=True)
    written = []
    for source in sorted(rules.glob("*.md")):
        target = short / source.name
        target.write_text(short_form(source.read_text(encoding="utf-8")), encoding="utf-8")
        written.append(target)
    for stale in short.glob("*.md"):
        if not (rules / stale.name).is_file():
            stale.unlink()
    return written


if __name__ == "__main__":
    for path in write_short(afc_root()):
        print(path.relative_to(afc_root()))
