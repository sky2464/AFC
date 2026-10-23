"""Own code graph extractor: files, classes, functions and imports.

Python is parsed with `ast`; JS/TS with regular expressions. Stdlib only.
`extract` reads the code tree and returns nodes and edges; it writes nothing.
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
JS_EXT = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]


@dataclass(frozen=True)
class Node:
    id: str
    kind: str  # file | module | class | function
    name: str
    path: str  # repo-relative, "" for external modules
    line: int


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str  # contains | imports | inherits | defines


def file_id(rel: str) -> str:
    return f"file:{rel}"


def module_node(name: str) -> Node:
    return Node(f"module:{name}", "module", name, "", 0)


# ---------------------------------------------------------------- Python

def _py_package(rel: str) -> list[str]:
    parts = list(PurePosixPath(rel).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
        return parts  # a package's own dotted name is its package
    return parts[:-1]


def _resolve_relative(rel: str, level: int, module: str | None) -> str:
    pkg = _py_package(rel)
    if level > 1:
        pkg = pkg[: len(pkg) - (level - 1)] if level - 1 <= len(pkg) else []
    parts = pkg + (module.split(".") if module else [])
    return ".".join(parts)


def _base_name(expr: ast.expr) -> str | None:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        inner = _base_name(expr.value)
        return f"{inner}.{expr.attr}" if inner else expr.attr
    return None


def extract_python(path: Path, rel: str) -> tuple[list[Node], list[Edge]]:
    """Parse one Python file. Raises on syntax/decode errors (extract catches)."""
    source = path.read_bytes().decode("utf-8")
    tree = ast.parse(source, filename=rel)
    fid = file_id(rel)
    nodes = [Node(fid, "file", PurePosixPath(rel).name, rel, 1)]
    edges: list[Edge] = []
    local_classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}

    for stmt in ast.walk(tree):
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                edges.append(Edge(fid, f"module:{alias.name}", "imports"))
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.level:
                target = _resolve_relative(rel, stmt.level, stmt.module)
            else:
                target = stmt.module or ""
            if target:
                edges.append(Edge(fid, f"module:{target}", "imports"))
            for alias in stmt.names:
                # `from pkg import submodule` may name a module too.
                if alias.name != "*" and target:
                    edges.append(Edge(fid, f"module:{target}.{alias.name}", "imports?"))

    def visit(body: list[ast.stmt], owner: str | None, prefix: str) -> None:
        for item in body:
            if isinstance(item, ast.ClassDef):
                cid = f"class:{rel}:{prefix}{item.name}"
                nodes.append(Node(cid, "class", item.name, rel, item.lineno))
                edges.append(Edge(owner or fid, cid, "defines" if owner else "contains"))
                for base in item.bases:
                    name = _base_name(base)
                    if not name:
                        continue
                    if name in local_classes:
                        edges.append(Edge(cid, f"class:{rel}:{name}", "inherits"))
                    else:
                        edges.append(Edge(cid, f"module:{name}", "inherits"))
                visit(item.body, cid, f"{prefix}{item.name}.")
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = f"function:{rel}:{prefix}{item.name}"
                nodes.append(Node(fn, "function", item.name, rel, item.lineno))
                edges.append(Edge(owner or fid, fn, "defines" if owner else "contains"))

    visit(tree.body, None, "")
    return nodes, edges


# ---------------------------------------------------------------- JS / TS

_JS_IMPORT = re.compile(r"""\bimport\s+(?:[\w*{}\s,$]+?\s+from\s+)?["']([^"']+)["']""")
_JS_EXPORT_FROM = re.compile(r"""\bexport\s+[\w*{}\s,$]+?\s+from\s+["']([^"']+)["']""")
_JS_REQUIRE = re.compile(r"""\brequire\(\s*["']([^"']+)["']\s*\)""")
_JS_CLASS = re.compile(
    r"^[ \t]*(?:export\s+(?:default\s+)?)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)"
    r"(?:\s+extends\s+([A-Za-z_$][\w$.]*))?", re.M)
_JS_FUNC = re.compile(
    r"^[ \t]*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)",
    re.M)


def _resolve_js(path: Path, rel: str, spec: str) -> str:
    if not spec.startswith("."):
        return f"module:{spec}"
    base = path.parent / spec
    rel_base = PurePosixPath(os.path.normpath(PurePosixPath(rel).parent / spec).replace(os.sep, "/"))
    if base.is_file() and base.suffix in CODE_EXT:
        return file_id(str(rel_base))
    for ext in JS_EXT:
        if base.with_name(base.name + ext).is_file():
            return file_id(f"{rel_base}{ext}")
    for ext in JS_EXT:
        if (base / f"index{ext}").is_file():
            return file_id(f"{rel_base}/index{ext}")
    return f"module:{rel_base}"


def _line_of(source: str, offset: int) -> int:
    return source.count("\n", 0, offset) + 1


def extract_js(path: Path, rel: str) -> tuple[list[Node], list[Edge]]:
    """Scan one JS/TS file with regexes. Raises on decode errors."""
    source = path.read_bytes().decode("utf-8")
    fid = file_id(rel)
    nodes = [Node(fid, "file", PurePosixPath(rel).name, rel, 1)]
    edges: list[Edge] = []
    for pattern in (_JS_IMPORT, _JS_EXPORT_FROM, _JS_REQUIRE):
        for m in pattern.finditer(source):
            edges.append(Edge(fid, _resolve_js(path, rel, m.group(1)), "imports"))
    for m in _JS_CLASS.finditer(source):
        cid = f"class:{rel}:{m.group(1)}"
        nodes.append(Node(cid, "class", m.group(1), rel, _line_of(source, m.start(1))))
        edges.append(Edge(fid, cid, "contains"))
        if m.group(2):
            edges.append(Edge(cid, f"module:{m.group(2)}", "inherits"))
    for m in _JS_FUNC.finditer(source):
        fn = f"function:{rel}:{m.group(1)}"
        nodes.append(Node(fn, "function", m.group(1), rel, _line_of(source, m.start(1))))
        edges.append(Edge(fid, fn, "contains"))
    return nodes, edges


# ---------------------------------------------------------------- walk

def _iter_code_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if p.suffix in CODE_EXT and p.is_file():
                yield p, p.relative_to(root).as_posix()


def _py_module_files(files: list[str]) -> dict[str, str]:
    """Map dotted module names to repo-relative .py paths."""
    out = {}
    for rel in files:
        if not rel.endswith(".py"):
            continue
        parts = list(PurePosixPath(rel).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            out.setdefault(".".join(parts), rel)
    return out


def _link(nodes: list[Node], edges: list[Edge], files: list[str]) -> list[Edge]:
    """Resolve module:/inherits targets to repo files and classes."""
    modules = _py_module_files(files)
    imported: dict[str, set[str]] = {}  # file id -> imported module names
    classes: dict[str, list[str]] = {}  # bare class name -> class ids
    for n in nodes:
        if n.kind == "class":
            classes.setdefault(n.name, []).append(n.id)
    for e in edges:
        if e.kind == "imports" and e.dst.startswith("module:"):
            imported.setdefault(e.src, set()).add(e.dst[7:])

    out = []
    for e in edges:
        if e.kind == "imports?":
            # `from pkg import name`: keep only when name is itself a repo module.
            mod = e.dst[7:]
            if mod in modules:
                out.append(Edge(e.src, file_id(modules[mod]), "imports"))
            continue
        if e.kind == "imports" and e.dst.startswith("module:") and e.dst[7:] in modules:
            out.append(Edge(e.src, file_id(modules[e.dst[7:]]), "imports"))
            continue
        if e.kind == "inherits" and e.dst.startswith("module:"):
            name = e.dst[7:]
            short = name.rsplit(".", 1)[-1]
            candidates = classes.get(short, [])
            if len(candidates) > 1:
                src_path = e.src.split(":", 2)[1]
                own = [c for c in candidates if c.split(":", 2)[1] != src_path]
                candidates = own if len(own) == 1 else candidates
            if len(candidates) == 1:
                out.append(Edge(e.src, candidates[0], "inherits"))
                continue
        out.append(e)
    return out


def extract(code_path: Path) -> tuple[list[Node], list[Edge]]:
    """Walk `code_path` and return (nodes, edges) sorted by id. Never raises per file."""
    root = Path(code_path)
    nodes: list[Node] = []
    edges: list[Edge] = []
    files: list[str] = []
    for path, rel in _iter_code_files(root):
        files.append(rel)
        extractor = extract_python if path.suffix == ".py" else extract_js
        try:
            n, e = extractor(path, rel)
        except (SyntaxError, ValueError, UnicodeDecodeError, OSError, RecursionError):
            n, e = [Node(file_id(rel), "file", path.name, rel, 1)], []
        nodes.extend(n)
        edges.extend(e)

    edges = _link(nodes, edges, files)
    known = {n.id for n in nodes}
    for e in edges:
        if e.dst.startswith("module:") and e.dst not in known:
            nodes.append(module_node(e.dst[7:]))
            known.add(e.dst)
    unique_nodes = {n.id: n for n in nodes}
    final_nodes = [unique_nodes[k] for k in sorted(unique_nodes)]
    final_edges = sorted(set(edges), key=lambda e: (e.src, e.dst, e.kind))
    return final_nodes, final_edges
