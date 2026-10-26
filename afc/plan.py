"""Master plan helpers: table rows, spec ids, slices, header, log and compaction.

Pure text helpers plus workspace functions (next_id, compact, now_line). Where the plan lives is
a Space: a project's is `<workspace>/plan/`, Flight Control's own is `docs/`. The functions accept
either a Space or, as before, a project workspace folder. Standard library only.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

MASTER = "master-plan.md"
DONE_KEEP = 10
LOG_KEEP = 20
_LOG_HEADER = "| Date | Event |\n|---|---|\n"
_DONE_HEADER = "| ID | Title | Done | Spec | Release | Outcome |\n|---|---|---|---|---|---|\n"
DONE_COLUMNS = 6  # ID, Title, Done, Spec, Release, Outcome; older rows and archives have only four
_RELEASES_HEADER = ["| Release | Date | Specs |", "|---|---|---|"]


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
    if section == "Done":  # old 4-column rows grow to the 6 the header now has
        rows = [list(r) + [""] * (DONE_COLUMNS - len(r)) for r in rows]
        lines[idx[0]], lines[idx[1]] = _DONE_HEADER.split("\n")[:2]
    new = ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    lines[idx[1] + 1 : idx[-1] + 1] = new
    return "\n".join(lines)


def stamp_release(text: str, ids, version_name: str) -> str:
    """Put the version in the Release column of the Done rows for `ids` (rows with one are left alone)."""
    wanted = set(ids)
    out = []
    for r in read_rows(text, "Done"):
        r = list(r) + [""] * (DONE_COLUMNS - len(r))
        if r[0] in wanted and not r[4]:
            r[4] = version_name
        out.append(r)
    return write_rows(text, "Done", out)


def releases_rows(text: str, tags: dict, pending: str = "") -> list[list[str]]:
    """Releases table rows, newest first: one per tag (`tags` maps tag to date) plus an unreleased
    version that Done rows already name. Specs come from the Done rows' Release column."""
    from afc import version
    by_release: dict[str, list[str]] = {}
    for r in read_rows(text, "Done"):
        if len(r) > 4 and r[4]:
            by_release.setdefault(r[4], []).append(r[0])
    names = set(tags) | set(by_release) | ({pending} if pending else set())
    ordered = sorted((n for n in names if version.is_version(n)), key=version.key, reverse=True)
    return [[n, tags.get(n, "not tagged yet"), ", ".join(sorted(by_release.get(n, []))) or "-"] for n in ordered]


def set_releases(text: str, tags: dict, pending: str = "") -> str:
    """Write the `## Releases` table, computed from tags and the Done rows; the section goes right
    after `## Done` when the plan has none yet."""
    rows = releases_rows(text, tags, pending)
    body = _RELEASES_HEADER + ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    lines = text.split("\n")
    try:
        start, end = _section_span(lines, "Releases")
        lines[start:end] = [""] + body + [""]
    except ValueError:
        _, end = _section_span(lines, "Done")
        lines[end:end] = ["## Releases", ""] + body + [""]
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
    real_criteria = [b for b in _bullets(spec_text, "You'll know it works when") if not _placeholder(b)]
    if not real_criteria:
        missing.append("no criteria yet (what you will see when it works)")
    blocks = _slice_blocks(spec_text)
    if not blocks:
        missing.append("no slices yet")
    for n, block in enumerate(blocks, 1):
        if not re.search(r"you'll see it by\s+(?!<)\S", block, re.IGNORECASE):
            missing.append(f"slice {n} has no 'you'll see it by'")
    if blocks:
        tasks = _task_blocks(spec_text)
        absent = [str(n) for n in range(1, len(blocks) + 1) if not tasks.get(n)]
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
    elif real_criteria:
        notes.append("the criteria are not numbered, so they are not linked to slices")
    to_confirm = [text for settled, text in assumptions(spec_text) if not settled and text and not text.startswith("<")]
    return {
        "ready": not missing,
        **({"missing": missing} if missing else {}),
        **({"notes": notes} if notes else {}),
        **({"to_confirm": to_confirm} if to_confirm else {}),
    }


def _placeholder(bullet: str) -> bool:
    """A template line nobody has filled in yet: `<…>` or `A1. <…>`."""
    return bool(re.match(r"(?:A\d+\.\s*)?<", bullet.strip()))


def _task_blocks(spec_text: str) -> dict[int, bool]:
    """For each `Slice n:` heading under Tasks, whether it lists at least one real (non-template) task."""
    blocks: dict[int, bool] = {}
    current = None
    for line in _task_lines(spec_text):
        m = re.match(r"\s*Slice (\d+):", line)
        if m:
            current = int(m.group(1))
            blocks[current] = False
        elif current is not None and line.strip() and not _placeholder(line.strip().lstrip("-* ").strip()):
            blocks[current] = True
    return blocks


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
    """Rewrite Size/Status/Started/Done/Depends on the `Size: ... · Status: ...` line only.

    Depends is added at the end of the line when it is new; an empty value removes it."""
    lines = spec_text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("Size:") and "Status:" in line:
            for key in ("size", "status", "started", "done"):
                if key in fields:
                    name = key.capitalize()
                    value = cell(fields[key]) or "-"
                    line = re.sub(rf"({name}: )[^·]*?(\s*(?:·|$))", lambda m: m.group(1) + value + m.group(2), line, count=1)
            if "depends" in fields:
                value = cell(fields["depends"])
                line = re.sub(r"\s*·\s*Depends:[^·]*", "", line).rstrip()
                if value:
                    line += f" · Depends: {value}"
            lines[i] = line
            break
    return "\n".join(lines)


def depends(spec_text: str) -> list[str]:
    """Spec IDs named in the header's `Depends:` field (comma separated); none when absent."""
    for line in spec_text.split("\n"):
        if line.startswith("Size:") and "Status:" in line:
            m = re.search(r"Depends:\s*([^·]*)", line)
            return [d for d in re.split(r"[,\s]+", m.group(1).strip()) if d and d != "-"] if m else []
    return []


def header_size(spec_text: str) -> str:
    """The size on the spec's header line, or "" when there is none."""
    for line in spec_text.split("\n"):
        if line.startswith("Size:") and "Status:" in line:
            m = re.match(r"Size:\s*([^·\s]*)", line)
            return m.group(1) if m else ""
    return ""


def set_score(text: str, name: str, value: str, keep_before: bool = False) -> tuple[str, str]:
    """Replace the Now cell of the Scoreboard row called `name` (case-blind). The old value moves to
    Before only when `keep_before` is true. Returns (new text, old value)."""
    rows = read_rows(text, "Scoreboard")
    for r in rows:
        if r[0].lower() == name.strip().lower():
            old = r[1]
            r += [""] * (4 - len(r))
            r[1] = value
            if keep_before:
                r[2] = old
            return write_rows(text, "Scoreboard", rows), old
    raise ValueError(f"The Scoreboard has no measure called '{name}'. It has: " + ", ".join(r[0] for r in rows) + ".")


def events_path(space) -> Path:
    """events.jsonl: in the project's workspace, or (for Flight Control's own plan) the home folder."""
    if space.prefix == "FC":
        from .config import afc_home
        return afc_home() / "events.jsonl"
    return space.base.parent / "events.jsonl"


def findings_path(space) -> Path:
    """findings.md: in docs/ for Flight Control's own plan, in plan/ for a project."""
    return space.base / "findings.md"


_FINDING_ID = re.compile(r"\bF-(\d+)\b")
_FINDING_HEADER = "| ID | Finding | State | Found |\n|---|---|---|---|\n"


def next_finding_id(findings_text: str) -> str:
    """Next F-NNN id from the table rows (lines starting with |); F-001 when none exist yet."""
    table_lines = [ln for ln in findings_text.split("\n") if ln.lstrip().startswith("|")]
    nums = [int(m) for ln in table_lines for m in _FINDING_ID.findall(ln)]
    return f"F-{max(nums, default=0) + 1:03d}"


_PARKED_HEADER = "| ID | Title | Size | Why | Revisit |\n|---|---|---|---|---|\n"
_WAITING_HEADER = "| # | Step | Added |\n|---|---|---|\n"


def _ensure_section(text: str, heading: str, header: str, after: str) -> str:
    """Add `## heading` with its table header after `## after` when absent; return text unchanged when present."""
    lines = text.split("\n")
    try:
        _section_span(lines, heading)
        return text  # already there
    except ValueError:
        pass
    try:
        _, end = _section_span(lines, after)
    except ValueError:
        end = len(lines)
    lines[end:end] = ["", f"## {heading}", ""] + header.splitlines() + [""]
    return "\n".join(lines)


def add_parked(text: str, sid: str, title: str, size: str, why: str, revisit: str) -> str:
    """Add a row to the Parked table (creating the section after Next if absent)."""
    text = _ensure_section(text, "Parked", _PARKED_HEADER, "Next")
    rows = read_rows(text, "Parked")
    rows.append([sid, title, size, why, revisit])
    return write_rows(text, "Parked", rows)


def remove_parked(text: str, sid: str) -> tuple[str, list[str]]:
    """Remove the Parked row for sid; return (new text, removed row) or ValueError if absent."""
    rows = read_rows(text, "Parked")
    row = next((r for r in rows if r and r[0] == sid), None)
    if row is None:
        raise ValueError(f"{sid} is not in Parked.")
    return write_rows(text, "Parked", [r for r in rows if r[0] != sid]), row


def add_waiting(text: str, step: str, date: str) -> tuple[str, int]:
    """Add a row to Waiting on you (creating the section after Next if absent); return (text, number)."""
    text = _ensure_section(text, "Waiting on you", _WAITING_HEADER, "Next")
    rows = read_rows(text, "Waiting on you")
    n = max((int(r[0]) for r in rows if r and r[0].isdigit()), default=0) + 1
    rows.append([str(n), step, date])
    return write_rows(text, "Waiting on you", rows), n


def remove_waiting(text: str, n: int) -> str:
    """Remove row number n from Waiting on you; ValueError if absent."""
    rows = read_rows(text, "Waiting on you")
    kept = [r for r in rows if not (r and r[0] == str(n))]
    if len(kept) == len(rows):
        raise ValueError(f"No waiting step number {n}.")
    return write_rows(text, "Waiting on you", kept)


def add_finding(findings_text: str, fid: str, text: str, found: str) -> str:
    """Append one finding row to the All findings table; create the section if absent."""
    new_row = f"| {fid} | {cell(text)} | open | {cell(found)} |"
    lines = findings_text.split("\n")
    try:
        start, end = _section_span(lines, "All findings")
        # find last table row (after header+divider) and insert after it
        table = [i for i in range(start, end) if lines[i].lstrip().startswith("|")]
        if len(table) < 2:
            lines.insert(end, new_row)
        else:
            lines.insert(table[-1] + 1, new_row)
    except ValueError:
        lines += ["", "## All findings", "", *_FINDING_HEADER.splitlines(), new_row, ""]
    return "\n".join(lines)


def event(space, date: str, text: str) -> None:
    """Append one plan event (date, event, spec) to events.jsonl. Never touches the plan."""
    m = re.match(r"([A-Z]+-\d+)\b", text)
    path = events_path(space)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"date": date, "event": text, "spec": m.group(1) if m else ""}) + "\n")


def log(text: str, date: str, event: str) -> str:
    """Append a row to the Update log (oldest first)."""
    rows = read_rows(text, "Update log")
    rows.append([date, event])
    return write_rows(text, "Update log", rows)


_ROUTINE = re.compile(r"\b(started|done|added)\b")
_FACT = re.compile(r"\d{3,}|→|->|target|closed|renamed|dropped", re.IGNORECASE)


def is_routine(event_text: str) -> bool:
    """A started/done/added row that carries no number or reason (spec IDs do not count as numbers)."""
    bare = re.sub(r"[A-Z]+-\d+", "", event_text)
    return bool(_ROUTINE.search(event_text)) and not _FACT.search(bare)


def tidy_split(rows: list[list[str]]) -> tuple[list[list[str]], list[list[str]]]:
    """(routine rows to move to events.jsonl, rows to keep), each in log order."""
    routine = [r for r in rows if len(r) > 1 and is_routine(r[1])]
    kept = [r for r in rows if not (len(r) > 1 and is_routine(r[1]))]
    return routine, kept


def tidy(where, apply: bool = True) -> dict:
    """Move routine Update log rows to events.jsonl, then rewrite the plan without them.

    The events are appended first; if the plan cannot be written, events.jsonl is cut back to its
    earlier size, so both are left as they were. With apply=False nothing is written."""
    space = _space(where)
    text = space.master.read_text(encoding="utf-8")
    rows = read_rows(text, "Update log")
    routine, kept = tidy_split(rows)
    out = {"routine": [f"{r[0]} {r[1]}" for r in routine], "kept": [f"{r[0]} {r[1]}" for r in kept if len(r) > 1],
           "lines_before": len(text.split("\n")), "log_before": len(rows), "log_after": len(kept)}
    if not apply or not routine:
        out.update(applied=False, events_written=0, lines_after=out["lines_before"], log_after=len(kept) if apply else len(rows))
        if not apply:
            out["log_after"] = len(kept)
        return out
    path = events_path(space)
    path.parent.mkdir(parents=True, exist_ok=True)
    size = path.stat().st_size if path.is_file() else None
    try:
        for r in routine:
            event(space, r[0], r[1])
        new = write_rows(text, "Update log", kept)
        space.master.write_text(new, encoding="utf-8")
    except BaseException:
        if size is None:
            path.unlink(missing_ok=True)
        else:
            with path.open("r+b") as f:
                f.truncate(size)
        raise
    out.update(applied=True, events_written=len(routine), lines_after=len(new.split("\n")))
    return out


def longest_section(text: str) -> tuple[str, int]:
    """(heading, line count) of the plan's longest `## ` section."""
    lines = text.split("\n")
    marks = [i for i, ln in enumerate(lines) if ln.startswith("## ")] + [len(lines)]
    best = ("", 0)
    for a, b in zip(marks, marks[1:]):
        if b - a > best[1]:
            best = (lines[a][3:].strip(), b - a)
    return best


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
