import shutil
import tempfile
import unittest
from pathlib import Path

from afc.codegraph import Edge, extract

FIXTURE = Path(__file__).parent / "fixtures" / "sample-app"


def _listing(root: Path) -> list:
    return sorted((str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns)
                  for p in root.rglob("*"))


class CodeGraphTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "sample-app"
        shutil.copytree(FIXTURE, self.root)
        (self.root / ".git").mkdir()
        (self.root / ".git" / "hook.py").write_text("def x():\n    pass\n")
        (self.root / "node_modules" / "lib").mkdir(parents=True)
        (self.root / "node_modules" / "lib" / "index.js").write_text("export function f() {}\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_python_classes_functions_imports(self):
        nodes, edges = extract(self.root)
        ids = {n.id for n in nodes}
        self.assertIn("class:app/models.py:Order", ids)
        self.assertIn("function:app/models.py:Order.total", ids)
        self.assertIn("function:app/models.py:make_order", ids)
        self.assertIn(Edge("file:app/api.py", "file:app/models.py", "imports"), edges)
        self.assertIn(Edge("file:app/models.py", "module:json", "imports"), edges)
        self.assertIn(Edge("class:app/models.py:Order", "class:app/models.py:Base", "inherits"), edges)
        self.assertIn(Edge("class:app/api.py:Handler", "class:app/models.py:Base", "inherits"), edges)
        self.assertIn(Edge("class:app/models.py:Order", "function:app/models.py:Order.total", "defines"), edges)
        self.assertIn(Edge("file:app/models.py", "class:app/models.py:Order", "contains"), edges)

    def test_js_relative_import_resolved(self):
        nodes, edges = extract(self.root)
        ids = {n.id for n in nodes}
        self.assertIn(Edge("file:web/main.ts", "file:web/client.ts", "imports"), edges)
        self.assertIn(Edge("file:web/main.ts", "file:web/util.js", "imports"), edges)
        self.assertIn(Edge("file:web/client.ts", "module:axios", "imports"), edges)
        self.assertIn(Edge("class:web/main.ts:App", "class:web/client.ts:Client", "inherits"), edges)
        self.assertIn("function:web/client.ts:makeClient", ids)
        self.assertIn("function:web/main.ts:start", ids)

    def test_skip_dirs(self):
        nodes, _ = extract(self.root)
        self.assertTrue(nodes)
        self.assertFalse(any(n.path.startswith(("node_modules", ".git")) for n in nodes))

    def test_bad_syntax_does_not_raise(self):
        nodes, edges = extract(self.root)
        broken = [n for n in nodes if n.path == "broken.py"]
        self.assertEqual([n.id for n in broken], ["file:broken.py"])
        self.assertFalse(any("broken.py" in e.src for e in edges))

    def test_undecodable_file_does_not_raise(self):
        (self.root / "bad.js").write_bytes(b"\xff\xfe\x00import x from 'y'\xff")
        nodes, _ = extract(self.root)
        self.assertEqual([n.id for n in nodes if n.path == "bad.js"], ["file:bad.js"])

    def test_deterministic(self):
        a, b = extract(self.root), extract(self.root)
        self.assertEqual(a, b)
        self.assertEqual([n.id for n in a[0]], sorted(n.id for n in a[0]))

    def test_repo_left_untouched(self):
        before = _listing(self.root)
        extract(self.root)
        self.assertEqual(before, _listing(self.root))


if __name__ == "__main__":
    unittest.main()
