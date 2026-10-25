"""Upgrading the workspace (~/.A-FC) to the layout the installed code expects (FC-011 slice 5).

The workspace records its layout number in the `layout` file (missing means layout 0, the original).
A release that changes the layout ships a step module `afc/upgrade_NNN.py` with `run(home)`; step N
takes the workspace from layout N-1 to N. Steps run once each, in order. Before the first one,
`~/.A-FC/` is copied to `~/.A-FC/backups/<date>-<old version>/` (project code folders live elsewhere
and are never touched). If a step fails, the workspace is restored from that backup.
"""

import importlib
import pkgutil
import re
import shutil
from datetime import date
from pathlib import Path

LAYOUT = "layout"
BACKUPS = "backups"
STEP = re.compile(r"^upgrade_(\d+)$")


def recorded(home: Path) -> int:
    try:
        return max(int((Path(home) / LAYOUT).read_text(encoding="utf-8").strip()), 0)
    except (OSError, ValueError):
        return 0


def _record(home: Path, number: int) -> None:
    (Path(home) / LAYOUT).write_text(f"{number}\n", encoding="utf-8")


def shipped_steps() -> list[tuple[int, object]]:
    """The upgrade steps shipped in afc/, as (number, run function), in order."""
    import afc

    found = []
    for info in pkgutil.iter_modules(afc.__path__):
        match = STEP.match(info.name)
        if match:
            found.append((int(match.group(1)), importlib.import_module(f"afc.{info.name}").run))
    return sorted(found, key=lambda s: s[0])


def _content(home: Path):
    return [p for p in Path(home).iterdir() if p.name != BACKUPS]


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _copy(src: Path, dst: Path) -> None:
    if src.is_dir() and not src.is_symlink():
        shutil.copytree(src, dst, symlinks=True)
    else:
        shutil.copy2(src, dst, follow_symlinks=False)


def backup(home: Path, old_version: str, today: date | None = None) -> Path:
    base = Path(home) / BACKUPS / f"{(today or date.today()).isoformat()}-{old_version}"
    target, n = base, 1
    while target.exists():
        n += 1
        target = base.with_name(f"{base.name}-{n}")
    target.mkdir(parents=True)
    try:
        for item in _content(home):
            _copy(item, target / item.name)
    except OSError:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return target


def restore(home: Path, saved: Path) -> None:
    for item in _content(home):
        _remove(item)
    for item in Path(saved).iterdir():
        _copy(item, Path(home) / item.name)


def upgrade(home: Path, old_version: str, steps=None, today: date | None = None) -> dict:
    home = Path(home)
    steps = shipped_steps() if steps is None else sorted(steps, key=lambda s: s[0])
    start = recorded(home)
    todo = [(n, fn) for n, fn in steps if n > start]
    if not todo or not home.is_dir():
        return {"upgraded": False, "layout": start}
    try:
        saved = backup(home, old_version, today)
    except OSError:
        return {"upgraded": False, "layout": start, "failed": True,
                "summary": "Your workspace could not be backed up, so it was not upgraded and nothing was changed."}
    ran = []
    for number, run in todo:
        try:
            run(home)
            _record(home, number)
        except Exception as exc:  # any failing step: put the workspace back as it was
            try:
                restore(home, saved)
            except OSError:
                return {"upgraded": False, "failed": True, "restored": False, "backup": str(saved),
                        "summary": f"Workspace upgrade step {number} failed ({exc}) and the backup could not be put back; "
                                   f"your saved copy is in {saved}."}
            return {"upgraded": False, "failed": True, "restored": True, "step": number, "layout": start,
                    "backup": str(saved),
                    "summary": f"Workspace upgrade step {number} failed ({exc}), so your workspace was restored from the backup."}
        ran.append(number)
    return {"upgraded": True, "layout": ran[-1], "steps": ran, "backup": str(saved),
            "summary": f"Your workspace was upgraded; a backup is in {saved}."}
