"""Master plan helpers: table rows, spec ids, slices, header, log and compaction.

Pure text helpers plus two workspace functions (next_id, compact). `ws` is a
project workspace folder; the plan lives in `ws/plan/`. Standard library only.
"""

import re
from pathlib import Path

MASTER = "master-plan.md"
DONE_KEEP = 10
LOG_KEEP = 100
_LOG_HEADER = "| Date | Event |\n|---|---|\n"


def cell(value) -> str:
    """One table cell: `|` becomes `/`, all whitespace collapses to single spaces."""
    return " ".join(str(value).replace("|", "/").split())


def _section_span(lines: list[str], section: str) -> tuple[int, int]:
    """(start, end) line indexes of the body under `## section`; ValueError if absent."""
    heading = f"## {section}"
    for i, line in enumerate(lines):
        if line.strip() == heading:
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("## "):
                    end = j
                    break
            return i + 1, end
    raise ValueError(f"The master plan has no '{section}' section.")


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_rows(text: str, section: str) -> list[list[str]]:
    """Data rows of the section's table (header and divider skipped)."""
    lines = text.split("\n")
    start, end = _section_span(lines, section)
    table = [ln for ln in lines[start:end] if ln.lstrip().startswith("|")]
    return [_split_row(ln) for ln in table[2:]]


def write_rows(text: str, section: str, rows: list[list]) -> str:
    """Replace the data rows of the section's table; header and divider stay."""
    lines = text.split("\n")
    start, end = _section_span(lines, section)
    idx = [i for i in range(start, end) if lines[i].lstrip().startswith("|")]
    if len(idx) < 2:
        raise ValueError(f"The '{section}' section has no table.")
    new = ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    lines[idx[1] + 1 : idx[-1] + 1] = new
    return "\n".join(lines)


def slugify(title: str) -> str:
    """Lowercase, dash-separated, at most 40 chars; 'spec' when nothing is left."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-")
    return slug or "spec"


def next_id(ws: Path) -> str:
    """Next spec id (S-001...), counting plan rows, archive index and file names."""
    plan_dir = Path(ws) / "plan"
    texts = []
    for path in (plan_dir / MASTER, plan_dir / "archive" / "index.md"):
        if path.is_file():
            texts.append(path.read_text(encoding="utf-8"))
    for folder in (plan_dir / "specs", plan_dir / "archive"):
        if folder.is_dir():
            texts.extend(p.name for p in folder.iterdir())
    nums = [int(n) for t in texts for n in re.findall(r"\bS-(\d+)", t)]
    return f"S-{max(nums, default=0) + 1:03d}"


def all_slices(spec_text: str) -> list[tuple[bool, str]]:
    """(done, label) for each checkbox line under `## Slices`."""
    lines = spec_text.split("\n")
    try:
        start, end = _section_span(lines, "Slices")
    except ValueError:
        return []
    found = []
    for line in lines[start:end]:
        m = re.match(r"\s*- \[([ xX])\]\s*(.*)$", line)
        if m:
            found.append((m.group(1) != " ", m.group(2).strip()))
    return found


def open_slices(spec_text: str) -> list[str]:
    """Labels of the unticked slices, in order."""
    return [label for done, label in all_slices(spec_text) if not done]


def set_header(spec_text: str, **fields) -> str:
    """Rewrite Status/Started/Done on the `Size: ... · Status: ...` line only."""
    lines = spec_text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("Size:") and "Status:" in line:
            for key in ("status", "started", "done"):
                if key in fields:
                    name = key.capitalize()
                    value = cell(fields[key]) or "-"
                    line = re.sub(rf"({name}: )[^·]*?(\s*(?:·|$))", lambda m: m.group(1) + value + m.group(2), line, count=1)
            lines[i] = line
            break
    return "\n".join(lines)


def log(text: str, date: str, event: str) -> str:
    """Append a row to the Update log (oldest first)."""
    rows = read_rows(text, "Update log")
    rows.append([date, event])
    return write_rows(text, "Update log", rows)


def compact(ws: Path) -> None:
    """Keep 10 newest Done rows and 100 Update log rows; older log rows are archived."""
    plan_dir = Path(ws) / "plan"
    path = plan_dir / MASTER
    text = path.read_text(encoding="utf-8")
    original = text
    done = read_rows(text, "Done")
    if len(done) > DONE_KEEP:
        text = write_rows(text, "Done", done[:DONE_KEEP])
    rows = read_rows(text, "Update log")
    if len(rows) > LOG_KEEP:
        old, keep = rows[:-LOG_KEEP], rows[-LOG_KEEP:]
        by_year: dict[str, list[list[str]]] = {}
        for row in old:
            m = re.match(r"\d{4}", row[0]) if row else None
            by_year.setdefault(m.group(0) if m else "unknown", []).append(row)
        archive = plan_dir / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        for year, items in by_year.items():
            target = archive / f"updatelog-{year}.md"
            body = "".join(
                "| " + " | ".join(cell(c) for c in r) + " |\n" for r in items
            )
            if target.is_file():
                existing = target.read_text(encoding="utf-8")
                if not existing.endswith("\n"):
                    existing += "\n"
                target.write_text(existing + body, encoding="utf-8")
            else:
                target.write_text(f"# Update log {year}\n\n{_LOG_HEADER}{body}", encoding="utf-8")
        text = write_rows(text, "Update log", keep)
    if text != original:
        path.write_text(text, encoding="utf-8")
