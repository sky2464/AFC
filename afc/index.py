"""Rebuildable SQLite index: one per project workspace plus one cross-project.

Files are the truth. Each index can be thrown away and rebuilt from the
workspace (plan, resources, reports) and the project's code graph. The
cross-project index holds plans and findings only, never `resources/`.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path

from afc.codegraph import _iter_code_files, extract
from afc.config import afc_home
from afc.registry import load_registry

SCHEMA_VERSION = 1
INDEX_NAME = "index.db"
MAX_TEXT_BYTES = 1_000_000
DOC_KINDS = (("plan", "plan"), ("resources", "resource"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS docs(id TEXT PRIMARY KEY, project TEXT, kind TEXT, path TEXT, title TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(id UNINDEXED, project, title, body);
CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY, project TEXT, kind TEXT, name TEXT, path TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS edges(src TEXT, dst TEXT, kind TEXT, project TEXT, data TEXT);
CREATE INDEX IF NOT EXISTS edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS edges_dst ON edges(dst);
CREATE TABLE IF NOT EXISTS findings(project TEXT, report TEXT, check_name TEXT, status TEXT, detail TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS fingerprints(path TEXT PRIMARY KEY, sha256 TEXT, mtime REAL);
"""


class IndexSchemaError(Exception):
    """The index was written by a different schema version."""


def open_index(path: Path) -> sqlite3.Connection:
    """Open (creating if needed) an index at `path`. Checks the schema version."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.executescript(SCHEMA)
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None:
            conn.execute("INSERT INTO meta VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))
            conn.commit()
        elif row[0] != str(SCHEMA_VERSION):
            raise IndexSchemaError("schema mismatch")
    except BaseException:
        conn.close()
        raise
    return conn


# ---------------------------------------------------------------- sources


def _read_text(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if len(raw) > MAX_TEXT_BYTES or b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _title(rel: str, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return Path(rel).name


def _doc_files(ws: Path, include_resources: bool) -> list[tuple[str, str, Path]]:
    """(kind, rel, path) for every indexable document, sorted by rel."""
    out = [("plan", f"plan/{p.name}", p) for p in sorted((ws / "plan").glob("*.md")) if p.is_file()]
    for sub in ("specs", "archive"):
        out += [("plan", f"plan/{sub}/{p.name}", p) for p in sorted((ws / "plan" / sub).glob("*.md")) if p.is_file()]
    out.sort(key=lambda t: t[1])
    if include_resources and (ws / "resources").is_dir():
        for p in sorted((ws / "resources").rglob("*")):
            if p.is_file():
                out.append(("resource", p.relative_to(ws).as_posix(), p))
    return out


def _report_files(ws: Path) -> list[Path]:
    return sorted(p for p in (ws / "reports").glob("*.json") if p.is_file())


def _code_path(project: str) -> Path | None:
    try:
        entry = load_registry(afc_home()).get(project)
    except Exception:
        return None
    if entry is None or not entry.code_path:
        return None
    path = Path(entry.code_path)
    return path if path.is_dir() else None


def _fingerprint(path: Path) -> tuple[str, float]:
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime


def _sources(ws: Path, project: str) -> dict[str, Path]:
    """Every file the project index is built from, keyed by fingerprint path."""
    found = {rel: p for _, rel, p in _doc_files(ws, True)}
    found.update({f"reports/{p.name}": p for p in _report_files(ws)})
    code = _code_path(project)
    if code is not None:
        found.update({f"code/{rel}": p for p, rel in _iter_code_files(code)})
    return found


# ---------------------------------------------------------------- writers


def _put_doc(conn, project: str, kind: str, rel: str, path: Path) -> None:
    text = _read_text(path)
    if text is None:
        return
    doc_id = f"{project}:{rel}"
    title = _title(rel, text)
    conn.execute("INSERT INTO docs VALUES(?,?,?,?,?)", (doc_id, project, kind, rel, title))
    conn.execute("INSERT INTO docs_fts VALUES(?,?,?,?)", (doc_id, project, title, text))


def _drop_doc(conn, project: str, rel: str) -> None:
    doc_id = f"{project}:{rel}"
    conn.execute("DELETE FROM docs WHERE id=?", (doc_id,))
    conn.execute("DELETE FROM docs_fts WHERE id=?", (doc_id,))


def _put_findings(conn, ws: Path, project: str) -> None:
    conn.execute("DELETE FROM findings WHERE project=?", (project,))
    for path in _report_files(ws):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            created = str(data.get("created", ""))
            checks = data.get("checks", [])
            rows = [(project, path.stem, str(c["name"]), str(c["status"]), str(c.get("detail", "")), created)
                    for c in checks]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
        conn.executemany("INSERT INTO findings VALUES(?,?,?,?,?,?)", rows)


def _put_graph(conn, project: str) -> None:
    conn.execute("DELETE FROM nodes WHERE project=?", (project,))
    conn.execute("DELETE FROM edges WHERE project=?", (project,))
    code = _code_path(project)
    if code is None:
        return
    nodes, edges = extract(code)
    conn.executemany(
        "INSERT OR REPLACE INTO nodes VALUES(?,?,?,?,?,?)",
        [(n.id, project, n.kind, n.name, n.path, json.dumps({"line": n.line})) for n in nodes],
    )
    conn.executemany(
        "INSERT INTO edges VALUES(?,?,?,?,?)",
        [(e.src, e.dst, e.kind, project, "{}") for e in edges],
    )


def _put_fingerprints(conn, sources: dict[str, Path]) -> None:
    conn.execute("DELETE FROM fingerprints")
    rows = []
    for key, path in sorted(sources.items()):
        try:
            rows.append((key, *_fingerprint(path)))
        except OSError:
            continue
    conn.executemany("INSERT INTO fingerprints VALUES(?,?,?)", rows)


def _swap_build(target: Path, fill) -> Path:
    """Build a fresh index in target.tmp with fill(conn), then atomically replace target."""
    tmp = target.with_name(target.name + ".tmp")
    for leftover in (tmp, Path(f"{tmp}-wal"), Path(f"{tmp}-shm")):
        leftover.unlink(missing_ok=True)
    conn = open_index(tmp)
    try:
        with conn:
            fill(conn)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")
    finally:
        conn.close()
    for stale in (Path(f"{target}-wal"), Path(f"{target}-shm")):
        stale.unlink(missing_ok=True)
    os.replace(tmp, target)
    return target


# ---------------------------------------------------------------- builds


def rebuild_project_index(workspace: Path, project: str) -> Path:
    """Fully rebuild workspace/index.db from the workspace files and code graph."""
    ws = Path(workspace)

    def fill(conn):
        for kind, rel, path in _doc_files(ws, True):
            _put_doc(conn, project, kind, rel, path)
        _put_findings(conn, ws, project)
        _put_graph(conn, project)
        _put_fingerprints(conn, _sources(ws, project))

    return _swap_build(ws / INDEX_NAME, fill)


def refresh_project_index(workspace: Path, project: str) -> Path:
    """Update only what changed since the last build; rebuild when the index is unusable."""
    ws = Path(workspace)
    db = ws / INDEX_NAME
    if not db.exists():
        return rebuild_project_index(ws, project)
    try:
        conn = open_index(db)
    except (sqlite3.DatabaseError, IndexSchemaError):
        return rebuild_project_index(ws, project)
    try:
        old = {k: (s, m) for k, s, m in conn.execute("SELECT path, sha256, mtime FROM fingerprints")}
        sources = _sources(ws, project)
        current = {}
        for key, path in sources.items():
            try:
                current[key] = _fingerprint(path)
            except OSError:
                continue
        changed = {k for k in set(old) | set(current) if old.get(k) != current.get(k)}
        if changed:
            with conn:
                kinds = dict(DOC_KINDS)
                for key in sorted(changed):
                    top = key.split("/", 1)[0]
                    if top in kinds:
                        _drop_doc(conn, project, key)
                        if key in current:
                            _put_doc(conn, project, kinds[top], key, sources[key])
                if any(k.startswith("reports/") for k in changed):
                    _put_findings(conn, ws, project)
                if any(k.startswith("code/") for k in changed):
                    _put_graph(conn, project)
                _put_fingerprints(conn, {k: sources[k] for k in current})
    except sqlite3.DatabaseError:
        conn.close()
        return rebuild_project_index(ws, project)
    conn.close()
    return db


def rebuild_global_index(home: Path) -> Path:
    """Rebuild home/index.db from every project's plan and findings. Never resources."""
    home = Path(home)
    reg = load_registry(home)

    def fill(conn):
        for name in sorted(reg.projects):
            ws = Path(reg.projects[name].workspace_path)
            for kind, rel, path in _doc_files(ws, include_resources=False):
                _put_doc(conn, name, kind, rel, path)
            _put_findings(conn, ws, name)

    home.mkdir(parents=True, exist_ok=True)
    return _swap_build(home / INDEX_NAME, fill)


# ---------------------------------------------------------------- queries


def _fts_query(query: str) -> str:
    terms = [t.replace('"', '""') for t in query.split()]
    return " ".join(f'"{t}"' for t in terms)


def _read(db: Path) -> sqlite3.Connection:
    conn = open_index(Path(db))
    conn.row_factory = sqlite3.Row
    return conn


def search(db: Path, query: str, limit: int = 20) -> list[dict]:
    """Full-text search over indexed documents, best match first."""
    match = _fts_query(query)
    if not match:
        return []
    conn = _read(db)
    try:
        rows = conn.execute(
            "SELECT d.project, d.kind, d.path, d.title, "
            "snippet(docs_fts, 3, '[', ']', '…', 12) AS snippet "
            "FROM docs_fts JOIN docs d ON d.id = docs_fts.id "
            "WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?",
            (match, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def open_findings(db: Path, statuses=("fail", "warn")) -> list[dict]:
    """Findings with the given statuses from each project's latest report only."""
    if not statuses:
        return []
    conn = _read(db)
    try:
        marks = ",".join("?" * len(statuses))
        rows = conn.execute(
            "WITH latest AS (SELECT project, report FROM ("
            " SELECT project, report, ROW_NUMBER() OVER ("
            "  PARTITION BY project ORDER BY created DESC, report DESC) AS n"
            " FROM (SELECT DISTINCT project, report, created FROM findings)) WHERE n = 1) "
            "SELECT f.project, f.report, f.check_name, f.status, f.detail, f.created "
            "FROM findings f JOIN latest l ON f.project = l.project AND f.report = l.report "
            f"WHERE f.status IN ({marks}) ORDER BY f.project, f.check_name",
            tuple(statuses),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def neighbors(db: Path, name: str) -> list[dict]:
    """Nodes whose name or id is `name`, each with its incoming and outgoing links."""
    conn = _read(db)
    try:
        found = conn.execute(
            "SELECT id, kind, path FROM nodes WHERE name = ? OR id = ? ORDER BY id", (name, name)
        ).fetchall()
        out = []
        for n in found:
            incoming = conn.execute(
                "SELECT src AS id, kind FROM edges WHERE dst = ? ORDER BY src, kind", (n["id"],)
            ).fetchall()
            outgoing = conn.execute(
                "SELECT dst AS id, kind FROM edges WHERE src = ? ORDER BY dst, kind", (n["id"],)
            ).fetchall()
            out.append({"id": n["id"], "kind": n["kind"], "path": n["path"],
                        "in": [dict(r) for r in incoming], "out": [dict(r) for r in outgoing]})
    finally:
        conn.close()
    return out
