"""Tests for the rebuildable project and cross-project index."""

import json
import os
import sqlite3
from pathlib import Path

from afc.index import (
    SCHEMA_VERSION,
    IndexSchemaError,
    neighbors,
    open_findings,
    open_index,
    rebuild_global_index,
    rebuild_project_index,
    refresh_project_index,
    search,
)
from afc.registry import Project, Registry, save_registry
from afc.workspace import create_workspace
from tests.helpers import AfcTestCase, run_cli

TABLES = ("meta", "docs", "docs_fts", "nodes", "edges", "findings", "fingerprints")


def rows(db: Path) -> dict:
    conn = sqlite3.connect(str(db))
    try:
        return {t: sorted(conn.execute(f"SELECT * FROM {t}").fetchall()) for t in TABLES}
    finally:
        conn.close()


def sidecar(ws: Path, stem: str, created: str, checks: list[tuple[str, str, str]]) -> None:
    data = {"label": stem, "created": created, "summary": "",
            "checks": [{"name": n, "status": s, "detail": d} for n, s, d in checks]}
    (ws / "reports" / f"{stem}.json").write_text(json.dumps(data), encoding="utf-8")


class IndexTests(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.reg = Registry()
        self.ws = self._project("kong-gateway-lab")
        self.reg.set_active("kong-gateway-lab")
        save_registry(self.home, self.reg)

    def _project(self, name: str) -> Path:
        ws = create_workspace(self.home, name)
        code = self.tmp / name
        (code / "app").mkdir(parents=True)
        (code / "app" / "routes.py").write_text(
            "from app.db import connect\n\n\ndef list_orders():\n    return connect()\n", encoding="utf-8")
        (code / "app" / "db.py").write_text("def connect():\n    return 1\n", encoding="utf-8")
        (ws / "plan" / "progress.md").write_text("# Progress\nfirst slice done\n", encoding="utf-8")
        self.reg.add(Project(name=name, code_path=str(code), workspace_path=str(ws)))
        save_registry(self.home, self.reg)
        return ws

    def test_open_index_wal_and_schema(self):
        conn = open_index(self.tmp / "x.db")
        try:
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
            self.assertEqual(conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0],
                             str(SCHEMA_VERSION))
            conn.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
            conn.commit()
        finally:
            conn.close()
        with self.assertRaisesRegex(IndexSchemaError, "schema mismatch"):
            open_index(self.tmp / "x.db")

    def test_rebuild_equals_fresh_build(self):
        a = rows(rebuild_project_index(self.ws, "kong-gateway-lab"))
        (self.ws / "index.db").unlink()
        self.assertEqual(a, rows(rebuild_project_index(self.ws, "kong-gateway-lab")))
        self.assertFalse((self.ws / "index.db.tmp").exists())

    def test_search_finds_decision(self):
        (self.ws / "plan/decisions.md").write_text("# Decisions\n2026-10-21 chose DB-less Kong mode\n")
        rebuild_project_index(self.ws, "kong-gateway-lab")
        hit = search(self.ws / "index.db", "DB-less")[0]
        self.assertEqual(hit["path"], "plan/decisions.md")
        self.assertEqual(hit["title"], "Decisions")
        self.assertEqual(hit["kind"], "plan")

    def test_resources_searchable_in_project_index(self):
        (self.ws / "resources/policy.md").write_text("Contoso tenant secret process")
        (self.ws / "resources/blob.bin").write_bytes(b"\x00\x01Contoso")
        db = rebuild_project_index(self.ws, "kong-gateway-lab")
        hits = search(db, "Contoso")
        self.assertEqual([(h["kind"], h["path"]) for h in hits], [("resource", "resources/policy.md")])

    def test_corrupt_index_rebuilt(self):
        (self.ws / "index.db").write_bytes(b"garbage")
        self.assertTrue(search(refresh_project_index(self.ws, "kong-gateway-lab"), "Decisions") is not None)
        self.assertTrue(search(self.ws / "index.db", "Progress"))

    def test_schema_mismatch_rebuilt(self):
        db = rebuild_project_index(self.ws, "kong-gateway-lab")
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE meta SET value='0' WHERE key='schema_version'")
        conn.commit()
        conn.close()
        refresh_project_index(self.ws, "kong-gateway-lab")
        open_index(db).close()  # no IndexSchemaError

    def test_global_index_never_contains_resources(self):
        (self.ws / "resources/policy.md").write_text("Contoso tenant secret process")
        g = rebuild_global_index(self.home)
        self.assertEqual(search(g, "Contoso"), [])
        conn = sqlite3.connect(str(g))
        try:
            self.assertEqual(conn.execute("SELECT count(*) FROM docs WHERE path LIKE 'resources/%'").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM docs_fts WHERE body LIKE '%Contoso%'").fetchone()[0], 0)
        finally:
            conn.close()
        self.assertTrue(search(g, "Progress"))

    def test_open_findings_across_projects(self):
        other = self._project("billing-api")
        sidecar(self.ws, "2026-10-20-0900-old", "2026-10-20T09:00:00", [("semgrep", "warn", "old finding")])
        sidecar(self.ws, "2026-10-21-0900-new", "2026-10-21T09:00:00",
                [("semgrep", "warn", "/orders has no rate limit"), ("secrets", "pass", "no secrets")])
        sidecar(other, "2026-10-21-1000-x", "2026-10-21T10:00:00", [("npm audit", "fail", "2 vulnerable deps")])
        found = open_findings(rebuild_global_index(self.home))
        self.assertEqual(
            [(f["project"], f["check_name"], f["status"], f["detail"]) for f in found],
            [("billing-api", "npm audit", "fail", "2 vulnerable deps"),
             ("kong-gateway-lab", "semgrep", "warn", "/orders has no rate limit")],
        )

    def test_refresh_picks_up_changed_file(self):
        db = rebuild_project_index(self.ws, "kong-gateway-lab")
        self.assertEqual(search(db, "kumquat"), [])
        progress = self.ws / "plan/progress.md"
        progress.write_text("# Progress\nkumquat slice shipped\n")
        os.utime(progress, (1, 1))
        refresh_project_index(self.ws, "kong-gateway-lab")
        self.assertEqual(search(db, "kumquat")[0]["path"], "plan/progress.md")
        self.assertEqual(search(db, "first"), [])
        (self.ws / "plan/progress.md").unlink()
        refresh_project_index(self.ws, "kong-gateway-lab")
        self.assertEqual(search(db, "kumquat"), [])

    def test_refresh_equals_rebuild(self):
        rebuild_project_index(self.ws, "kong-gateway-lab")
        (self.ws / "plan/decisions.md").write_text("# Decisions\nnew\n")
        sidecar(self.ws, "r1", "2026-10-21T09:00:00", [("semgrep", "warn", "x")])
        code = self.tmp / "kong-gateway-lab" / "app" / "extra.py"
        code.write_text("def extra():\n    pass\n")
        a = rows(refresh_project_index(self.ws, "kong-gateway-lab"))
        (self.ws / "index.db").unlink()
        self.assertEqual(a, rows(rebuild_project_index(self.ws, "kong-gateway-lab")))

    def test_graph_nodes_store_line_and_neighbors(self):
        db = rebuild_project_index(self.ws, "kong-gateway-lab")
        conn = sqlite3.connect(str(db))
        data = conn.execute("SELECT data FROM nodes WHERE name='list_orders'").fetchone()[0]
        conn.close()
        self.assertEqual(json.loads(data), {"line": 4})
        [hit] = neighbors(db, "file:app/db.py")
        self.assertEqual(hit["id"], "file:app/db.py")
        self.assertIn("file:app/routes.py", [link["id"] for link in hit["in"]])
        self.assertTrue(hit["out"])
        self.assertEqual(neighbors(db, "nothing-here"), [])

    def test_cli_commands(self):
        (self.ws / "plan/decisions.md").write_text("# Decisions\nchose DB-less Kong mode\n")
        (self.ws / "resources/policy.md").write_text("Contoso tenant secret process")
        sidecar(self.ws, "r1", "2026-10-21T09:00:00", [("semgrep", "warn", "x")])
        code, out = run_cli(["index", "rebuild"])
        self.assertEqual((code, out["scope"]), (0, "kong-gateway-lab"))
        code, out = run_cli(["index", "refresh"])
        self.assertEqual(code, 0)
        code, out = run_cli(["index", "search", "Contoso"])
        self.assertEqual([r["path"] for r in out["results"]], ["resources/policy.md"])
        code, out = run_cli(["index", "rebuild", "--all"])
        self.assertEqual((code, out["scope"]), (0, "all"))
        code, out = run_cli(["index", "search", "Contoso", "--all"])
        self.assertEqual(out["results"], [])
        code, out = run_cli(["index", "search", "DB-less", "--all"])
        self.assertEqual(out["results"][0]["project"], "kong-gateway-lab")
        code, out = run_cli(["index", "findings", "--all"])
        self.assertEqual([f["check_name"] for f in out["findings"]], ["semgrep"])
        code, out = run_cli(["graph", "impact", "connect"])
        self.assertEqual(code, 0)
        self.assertEqual(out["matches"][0]["id"], "function:app/db.py:connect")

    def test_cli_no_active_project(self):
        self.reg.active_name = None
        save_registry(self.home, self.reg)
        code, out = run_cli(["index", "refresh"])
        self.assertEqual(code, 1)
        self.assertIn("No active project", out["error"])
