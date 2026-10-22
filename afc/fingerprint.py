"""Fingerprints of company resources, so their text can be spotted outside the workspace.

A fingerprint is the sha256 of a normalized unit at least MIN_LINE characters long: a
line, a paragraph with its line breaks collapsed, or a sentence of either (split on
. ! ? ; :), after leading list/quote/comment markers are removed. Whole files of at
least MIN_LINE normalized characters are fingerprinted by their bytes too. Per-file
results are cached in `<workspace>/.afc-fingerprints.json`, so only changed files rehash.
"""

import hashlib
import json
import re
from pathlib import Path

MIN_LINE = 40
CACHE_NAME = ".afc-fingerprints.json"
CACHE_VERSION = 2
_SPACE = re.compile(r"\s+")
_PIECE = re.compile(r"[.!?;:]+(?:\s|$)")
_MARKER = re.compile(r"^(?:[-*>#+]+|\d+[.)])\s+")
_MAX_FILE_BYTES = 20_000_000


def normalize(line: str) -> str:
    """Strip, collapse whitespace, lowercase."""
    return _SPACE.sub(" ", line.strip()).lower()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strip_markers(line: str) -> str:
    line = line.strip()
    while (m := _MARKER.match(line)):
        line = line[m.end():]
    return line


def _with_pieces(norm: str) -> list[str]:
    return [norm, *(p.strip() for p in _PIECE.split(norm))]


def _units(text: str) -> set[str]:
    """Normalized lines, collapsed paragraphs and their sentences, long enough to hash."""
    candidates: list[str] = []
    paragraph: list[str] = []
    for raw in [*text.splitlines(), ""]:
        line = normalize(_strip_markers(raw))
        if line:
            candidates.extend(_with_pieces(line))
            paragraph.append(line)
        elif paragraph:
            candidates.extend(_with_pieces(" ".join(paragraph)))
            paragraph = []
    return {c for c in candidates if len(c) >= MIN_LINE}


def _text_fingerprints(text: str) -> set[str]:
    return {_sha(u.encode()) for u in _units(text)}


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
    if b"\0" in data:
        return {_sha(data)} if len(data) >= MIN_LINE else set()
    text = data.decode("utf-8", errors="replace")
    fps = _text_fingerprints(text)
    if len(normalize(text)) >= MIN_LINE:
        fps.add(_sha(data))
    return fps


def build_fingerprints(resources: Path) -> set[str]:
    """Fingerprints of every text unit and every whole file under resources/."""
    fps: set[str] = set()
    for path in _files(resources):
        fps |= _file_fingerprints(path)
    return fps


def _read_cache(cache: Path) -> dict:
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("v") == CACHE_VERSION and isinstance(data.get("files"), dict):
            return data["files"]
    except (OSError, ValueError):
        pass
    return {}


def load_fingerprints(workspace: Path) -> set[str]:
    """Fingerprints of workspace/resources; files whose mtime_ns or size changed rehash."""
    resources = workspace / "resources"
    cache = workspace / CACHE_NAME
    old = _read_cache(cache)
    files: dict[str, dict] = {}
    for path in _files(resources):
        try:
            st = path.stat()
        except OSError:
            continue
        rel = str(path.relative_to(resources))
        entry = old.get(rel)
        if (isinstance(entry, dict) and entry.get("mtime_ns") == st.st_mtime_ns
                and entry.get("size") == st.st_size and isinstance(entry.get("fps"), list)):
            files[rel] = entry
        else:
            files[rel] = {"mtime_ns": st.st_mtime_ns, "size": st.st_size,
                          "fps": sorted(_file_fingerprints(path))}
    if files != old:
        try:
            cache.write_text(json.dumps({"v": CACHE_VERSION, "files": files}), encoding="utf-8")
        except OSError:
            pass  # no cache this time; the fingerprints are still right
    return {fp for entry in files.values() for fp in entry["fps"]}


def leaks(text: str, fps: set[str]) -> bool:
    """True when text as a whole, or any long-enough unit of it, matches a fingerprint."""
    if not fps:
        return False
    if len(normalize(text)) >= MIN_LINE and _sha(text.encode("utf-8", errors="replace")) in fps:
        return True
    return any(fp in fps for fp in _text_fingerprints(text))
