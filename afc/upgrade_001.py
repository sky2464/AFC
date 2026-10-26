"""Workspace layout 0 -> 1 (FC-036): remove the old global maintenance switch `maintain`."""

from pathlib import Path


def run(home: Path) -> None:
    (Path(home) / "maintain").unlink(missing_ok=True)
