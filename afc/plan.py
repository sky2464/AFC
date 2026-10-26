"""Master plan helpers: table rows, spec ids, slices, header, log and compaction.

Pure text helpers plus workspace functions (next_id, compact, now_line). Where the plan lives is
a Space: a project's is `<workspace>/plan/`, Flight Control's own is `docs/`. The functions accept
either a Space or, as before, a project workspace folder. Standard library only.
"""

import re
from dataclasses import dataclass
from pathlib import Path

MASTER = "master-plan.md"
DONE_KEEP = 10
LOG_KEEP = 100
_LOG_HEADER = "| Date | Event |\n|---|---|\n"
_DONE_HEADER = "| ID | Title | Done | Spec |\n|---|---|---|---|\n"


@dataclass(frozen=True)
class Space:
    """A folder holding master-plan.md, its specs/ and the archive of finished specs."""

    base: Path
    archive: str = "archive"  # relative to base
    prefix: str = "S"  # spec IDs are <prefix>-001...: S for projects, FC for Flight Control itself

    @property
    def master(self) -> Path:
        return self.base / MASTER

    @property
    def specs(self) -> Path:
        return self.base / "specs"

    @property
    def archive_dir(self) -> Path:
        return self.base / self.archive


def project_space(ws: Path) -> Space:
    return Space(Path(ws) / "plan")


def flight_control_space(root: Path) -> Space:
    """Flight Control's own plan: docs/master-plan.md, docs/specs/ and docs/specs/archive/."""
    return Space(Path(root) / "docs", archive="specs/archive", prefix="FC")


def _space(where) -> Space:
    return where if isinstance(where, Space) else project_space(where)


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


def set_goal(text: str, goal: str) -> str:
    """Replace the body of `## Goal` with one line; every other section stays as it is."""
    lines = text.split("\n")
    start, end = _section_span(lines, "Goal")
    lines[start:end] = ["", goal, ""]
    return "\n".join(lines)


def slugify(title: str) -> str:
    """Lowercase, dash-separated, at most 40 chars cut at a word end; 'spec' when nothing is left."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(slug) > 40:
        head = slug[:40]
        if slug[40] != "-" and "-" in head:  # the 41st character continues a word: drop it
            head = head[: head.rindex("-")]
        slug = head
    return slug.strip("-") or "spec"


def next_id(where) -> str:
    """Next spec id (S-001... or FC-001...), counting plan rows, archive index and file names.

    Only IDs with this plan's own prefix count, so the two numberings never mix."""
    space = _space(where)
    texts = []
    for path in (space.master, space.archive_dir / "index.md"):
        if path.is_file():
            texts.append(path.read_text(encoding="utf-8"))
    for folder in (space.specs, space.archive_dir):
        if folder.is_dir():
            texts.extend(p.name for p in folder.iterdir())
    nums = [int(n) for t in texts for n in re.findall(rf"\b{space.prefix}-(\d+)", t)]
    return f"{space.prefix}-{max(nums, default=0) + 1:03d}"


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


def unreadable_slices(spec_text: str) -> list[str]:
    """List items under `## Slices` that aren't checkbox lines, so `plan` can't see them."""
    lines = spec_text.split("\n")
    try:
        start, end = _section_span(lines, "Slices")
    except ValueError:
        return []
    found = []
    for line in lines[start:end]:
        m = re.match(r"(?:[-*]|\d+[.)])\s+(.*)$", line)  # unindented, so continuation lines don't count
        if m and not re.match(r"\[[ xX]\]", m.group(1)):
            found.append(m.group(1).strip())
    return found


def section_filled(spec_text: str, section: str) -> bool:
    """True when `## section` exists and has some text under it."""
    lines = spec_text.split("\n")
    try:
        start, end = _section_span(lines, section)
    except ValueError:
        return False
    return any(ln.strip() for ln in lines[start:end])


def _slice_blocks(spec_text: str) -> list[str]:
    """Each checkbox slice under `## Slices` with its wrapped continuation lines, as one string."""
    lines = spec_text.split("\n")
    try:
        start, end = _section_span(lines, "Slices")
    except ValueError:
        return []
    blocks: list[str] = []
    for line in lines[start:end]:
        if re.match(r"\s*- \[[ xX]\]", line):
            blocks.append(line.strip())
        elif blocks and line.strip():
            blocks[-1] += " " + line.strip()
    return blocks


def _bullets(spec_text: str, section: str) -> list[str]:
    lines = spec_text.split("\n")
    try:
        start, end = _section_span(lines, section)
    except ValueError:
        return []
    return [m.group(1).strip() for ln in lines[start:end] if (m := re.match(r"\s*[-*]\s+(.*)$", ln))]


def criteria(spec_text: str) -> list[str]:
    """Ids ('A1', 'A2', ...) of the numbered bullets under "You'll know it works when"."""
    found = []
    for bullet in _bullets(spec_text, "You'll know it works when"):
        m = re.match(r"(A\d+)\.", bullet)
        if m:
            found.append(m.group(1))
    return found


def proofs(label: str) -> list[str]:
    """Criterion ids a slice names with `(proves A1, A2)` at its end."""
    m = re.search(r"\(proves\s+([^)]*)\)\s*$", label.strip(), re.IGNORECASE)
    return re.findall(r"A\d+", m.group(1)) if m else []


def assumptions(spec_text: str) -> list[tuple[bool, str]]:
    """(settled, text) for each checkbox line under `## Assumptions to confirm`."""
    lines = spec_text.split("\n")
    try:
        start, end = _section_span(lines, "Assumptions to confirm")
    except ValueError:
        return []
    found = []
    for line in lines[start:end]:
        m = re.match(r"\s*- \[([ xX])\]\s*(.*)$", line)
        if m:
            found.append((m.group(1) != " ", m.group(2).strip()))
        elif found and line.strip() and line.startswith((" ", "\t")):
            found[-1] = (found[-1][0], found[-1][1] + " " + line.strip())
    return found


def readiness(spec_text: str, fc: bool) -> dict:
    """Is a spec ready for build? {'ready': bool} plus 'missing' (plain words) when it is not,
    'notes' (never a block) for older specs whose criteria are not numbered, and 'to_confirm'
    (never a block) listing the assumptions not yet settled.

    Checks Goal, Out of scope, criteria, slices (each with "you'll see it by"), Tasks (a `Slice n:`
    line per slice) and, for Flight Control's own specs, "Reaches the apps"."""
    missing: list[str] = []
    for section, what in (("Goal", "no goal yet"), ("Out of scope", "nothing said about what is out of scope")):
        if not section_filled(spec_text, section):
            missing.append(what)
    if fc and not section_filled(spec_text, "Reaches the apps"):
        missing.append("no 'Reaches the apps' section filled in")
    if not _bullets(spec_text, "You'll know it works when"):
        missing.append("no criteria yet (what you will see when it works)")
    blocks = _slice_blocks(spec_text)
    if not blocks:
        missing.append("no slices yet")
    for n, block in enumerate(blocks, 1):
        if not re.search(r"you'll see it by\s+(?!<)\S", block, re.IGNORECASE):
            missing.append(f"slice {n} has no 'you'll see it by'")
    if blocks:
        tasks = "\n".join(_task_lines(spec_text))
        absent = [str(n) for n in range(1, len(blocks) + 1) if not re.search(rf"^\s*Slice {n}:", tasks, re.M)]
        if absent:
            missing.append("no tasks for slice " + ", ".join(absent))
    notes: list[str] = []
    numbered = criteria(spec_text)
    named = [proofs(b) for b in blocks]
    if numbered or any(named):
        for crit in numbered:
            if not any(crit in ids for ids in named):
                missing.append(f"{crit} has no slice that proves it")
        for n, ids in enumerate(named, 1):
            for crit in ids:
                if crit not in numbered:
                    missing.append(f"slice {n} says it proves {crit}, which is not in the criteria")
    elif _bullets(spec_text, "You'll know it works when"):
        notes.append("the criteria are not numbered, so they are not linked to slices")
    to_confirm = [text for settled, text in assumptions(spec_text) if not settled and text]
    return {
        "ready": not missing,
        **({"missing": missing} if missing else {}),
        **({"notes": notes} if notes else {}),
        **({"to_confirm": to_confirm} if to_confirm else {}),
    }


def _task_lines(spec_text: str) -> list[str]:
    lines = spec_text.split("\n")
    try:
        start, end = _section_span(lines, "Tasks")
    except ValueError:
        return []
    return lines[start:end]


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


def _archive_rows(space, prefix: str, heading: str, header: str, by_year: dict, undo: dict) -> None:
    """Append rows to archive/<prefix>-<year>.md, creating it with a heading; never replaces a file.

    `undo` remembers each file's earlier text (None if it did not exist) so a failure can put it back."""
    archive = space.archive_dir
    archive.mkdir(parents=True, exist_ok=True)
    for year, items in by_year.items():
        target = archive / f"{prefix}-{year}.md"
        body = "".join("| " + " | ".join(cell(c) for c in r) + " |\n" for r in items)
        existing = target.read_text(encoding="utf-8") if target.is_file() else None
        undo.setdefault(target, existing)
        if existing is None:
            target.write_text(f"# {heading} {year}\n\n{header}{body}", encoding="utf-8")
        else:
            if not existing.endswith("\n"):
                existing += "\n"
            target.write_text(existing + body, encoding="utf-8")


def _by_year(rows: list[list[str]], column: int) -> dict[str, list[list[str]]]:
    grouped: dict[str, list[list[str]]] = {}
    for row in rows:
        m = re.match(r"\d{4}", row[column]) if len(row) > column else None
        grouped.setdefault(m.group(0) if m else "unknown", []).append(row)
    return grouped


def compact(where) -> None:
    """Keep 10 newest Done rows and 100 Update log rows; older rows are archived first.

    The archive is written before the plan. If any write fails, archive files are put back as they
    were and the plan is left whole, so a retry cannot duplicate rows."""
    space = _space(where)
    path = space.master
    text = path.read_text(encoding="utf-8")
    original = text
    undo: dict = {}
    try:
        done = read_rows(text, "Done")
        if len(done) > DONE_KEEP:
            _archive_rows(space, "done", "Done", _DONE_HEADER, _by_year(done[DONE_KEEP:], 2), undo)
            text = write_rows(text, "Done", done[:DONE_KEEP])
        rows = read_rows(text, "Update log")
        if len(rows) > LOG_KEEP:
            _archive_rows(space, "updatelog", "Update log", _LOG_HEADER, _by_year(rows[:-LOG_KEEP], 0), undo)
            text = write_rows(text, "Update log", rows[-LOG_KEEP:])
        if text != original:
            path.write_text(text, encoding="utf-8")
    except BaseException:
        for target, before in undo.items():
            try:
                if before is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_text(before, encoding="utf-8")
            except OSError:
                pass
        raise


def now_line(where) -> str:
    """'S-002 Title (next slice: ...)' for the spec in Now; '' when there is none."""
    space = _space(where)
    path = space.master
    if not path.is_file():
        return ""
    rows = read_rows(path.read_text(encoding="utf-8"), "Now")
    if not rows:
        return ""
    row = rows[0]
    line = f"{row[0]} {row[1]}"
    m = re.search(r"\(([^)]*)\)", row[3] if len(row) > 3 else "")
    spec = space.base / m.group(1) if m else None
    if spec is None or not spec.is_file():
        return line
    slices = all_slices(spec.read_text(encoding="utf-8"))
    if not slices:
        return line
    open_ = [label for done, label in slices if not done]
    return f"{line} (next slice: {open_[0]})" if open_ else f"{line} (all slices done)"
