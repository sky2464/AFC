"""Undo list for a command that writes files, so a failure leaves no partial state."""

import shutil
from pathlib import Path


class Undo:
    """What a failed command must undo: folders it created and the settings file it changed.

    Paths are recorded with mark() before anything is created. rollback() removes
    only the recorded paths that exist now, and restores the settings file bytes.
    """

    def __init__(self, settings: Path) -> None:
        self._settings = settings
        self._fresh: list[Path] = []
        self._settings_before: bytes | None = None
        self._settings_saved = False
        self._restorers: list = []

    def on_rollback(self, restore) -> None:
        """Run restore() during rollback (for files other than the settings file)."""
        self._restorers.append(restore)

    def mark(self, paths: list[Path]) -> None:
        """Record each path that does not exist yet. Call before creating anything."""
        self._fresh.extend(p for p in paths if not p.exists() and not p.is_symlink())

    def save_settings(self) -> None:
        """Remember the settings file as it is now, before the command changes it."""
        self._settings_before = self._settings.read_bytes() if self._settings.exists() else None
        self._settings_saved = True

    def rollback(self) -> None:
        if self._settings_saved:
            try:
                if self._settings_before is None:
                    self._settings.unlink(missing_ok=True)
                else:
                    self._settings.write_bytes(self._settings_before)
            except OSError:
                pass
        for restore in reversed(self._restorers):
            try:
                restore()
            except OSError:
                pass
        for path in reversed(self._fresh):
            _remove(path)


def _remove(path: Path) -> None:
    """Best-effort removal, used only for paths this call created."""
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
    except OSError:
        pass
