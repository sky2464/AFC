"""Fingerprints of company resources, so their text can be spotted outside the workspace.

A fingerprint is the sha256 of a normalized line (or sentence-like piece of one) at
least MIN_LINE characters long, or of a whole resource file's bytes. The set is cached
in `<workspace>/.afc-fingerprints.json` and rebuilt when any resource file changes.
"""

import hashlib
import json
import re
from pathlib import Path

MIN_LINE = 40
CACHE_NAME = ".afc-fingerprints.json"
_SPACE = re.compile(r"\s+")
_PIECE = re.compile(r"[.!?;:]+(?:\s|$)")
_MAX_FILE_BYTES = 20_000_000


def normalize(line: str) -> str:
    """Strip, collapse whitespace, lowercase."""
    return _SPACE.sub(" ", line.strip()).lower()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _units(text: str) -> set[str]:
    """Normalized lines and their sentence pieces that are long enough to fingerprint."""
    out: set[str] = set()
    for line in text.splitlines():
        norm = normalize(line)
        candidates = [norm, *(p.strip() for p in _PIECE.split(norm))]
        out.update(c for c in candidates if len(c) >= MIN_LINE)
    return out


def _files(resources: Path) -> list[Path]:
    if not resources.is_dir():
        return []
    return sorted(p for p in resources.rglob("*") if p.is_file())


def _file_fingerprints(path: Path) -> set[str]:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return set()
        data = path.read_bytes()
    except OSError:
        return set()
    fps = {_sha(data)}
    if b"\0" not in data:
        text = data.decode("utf-8", errors="replace")
        fps.update(_sha(u.encode()) for u in _units(text))
    return fps


def build_fingerprints(resources: Path) -> set[str]:
    """Fingerprints of every text line and every whole file under resources/."""
    fps: set[str] = set()
    for path in _files(resources):
        fps |= _file_fingerprints(path)
    return fps


def _mtimes(resources: Path) -> dict[str, float]:
    out = {}
    for path in _files(resources):
        try:
            out[str(path.relative_to(resources))] = path.stat().st_mtime
        except OSError:
            continue
    return out


def load_fingerprints(workspace: Path) -> set[str]:
    """Cached fingerprints of workspace/resources, rebuilt when any file or mtime changed."""
    resources = workspace / "resources"
    cache = workspace / CACHE_NAME
    mtimes = _mtimes(resources)
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        if data.get("mtimes") == mtimes:
            return set(data["fingerprints"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    fps = build_fingerprints(resources)
    try:
        cache.write_text(json.dumps({"mtimes": mtimes, "fingerprints": sorted(fps)}),
                         encoding="utf-8")
    except OSError:
        pass  # no cache this time; the fingerprints are still right
    return fps


def leaks(text: str, fps: set[str]) -> bool:
    """True when text, or any long-enough line or sentence of it, matches a fingerprint."""
    if not fps:
        return False
    if _sha(text.encode("utf-8", errors="replace")) in fps:
        return True
    return any(_sha(u.encode()) in fps for u in _units(text))
