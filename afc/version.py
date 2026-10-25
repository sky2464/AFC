"""Flight Control's own version: the VERSION file at the root, and version ordering.

Versions look like v0.01a: a "v", numbers split by dots, then an optional lowercase letter.
They compare number by number (so v0.02a < v0.10a), then by letter.
"""

import re
from pathlib import Path

PATTERN = re.compile(r"^v(\d+(?:\.\d+)+)([a-z]?)$")


class VersionError(ValueError):
    pass


def _match(text):
    # anything that is not text (a stored 5 or ["x"], say) is simply not a version
    return PATTERN.match(text) if isinstance(text, str) else None


def is_version(text: str) -> bool:
    return bool(_match(text))


def key(text: str) -> tuple:
    match = _match(text)
    if not match:
        raise VersionError(f"{text!r} is not a Flight Control version like v0.01a.")
    return tuple(int(n) for n in match.group(1).split(".")), match.group(2)


def is_newer(candidate: str, current: str) -> bool:
    return key(candidate) > key(current)


def newest(names) -> str | None:
    found = [n for n in names if is_version(n)]
    return max(found, key=key) if found else None


def installed(root: Path) -> str:
    path = Path(root) / "VERSION"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        raise VersionError("Flight Control's VERSION file is missing.") from None
    if not is_version(text):
        raise VersionError(f"Flight Control's VERSION file holds {text!r}, not a version like v0.01a.")
    return text
