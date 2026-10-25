"""Flight Control's own version: read from the VERSION file, ordered by release.

A version is a major number, a minor number and an optional letter, written 0.02a. Versions
compare by major, then minor as a number, then letter; the bare version (no letter) comes before a.
The VERSION file at the repo root holds the last published release of this copy.
"""

import re
from pathlib import Path
from typing import NamedTuple

VERSION_FILE = "VERSION"
PATTERN = re.compile(r"v?(\d+)\.(\d+)([a-z]?)")


class VersionError(ValueError):
    """A version that cannot be read, in plain words."""


class Version(NamedTuple):
    major: int
    minor: int
    letter: str

    def __str__(self) -> str:
        return f"{self.major}.{self.minor:02d}{self.letter}"

    def label(self) -> str:
        """The version as people see it in the welcome: v0.02a."""
        return f"v{self}"


def parse(text: str) -> Version:
    """Read 0.02a or v0.02a (spaces and line ends ignored). Anything else raises VersionError."""
    cleaned = text.strip()
    match = PATTERN.fullmatch(cleaned)
    if match is None:
        raise VersionError(f"{cleaned!r} is not a version like 0.02a.")
    major, minor, letter = match.groups()
    return Version(int(major), int(minor), letter)


def read(root: Path) -> Version:
    """The version in root/VERSION: the last published release of this copy."""
    path = root / VERSION_FILE
    if not path.is_file():
        raise VersionError(f"There is no VERSION file at {path}.")
    try:
        return parse(path.read_text(encoding="utf-8"))
    except VersionError as exc:
        raise VersionError(f"The VERSION file is wrong: {exc}") from exc
