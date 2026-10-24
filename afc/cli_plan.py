"""Plan commands: plan, plan add|start|done.

Registered into the main parser by afc.cli through register(). They move a spec from
Next to Now to Done in the master plan and keep its file in plan/specs/ or plan/archive/.
Each handler returns one JSON-able dict, like every other Flight Control command.
"""

import argparse
import re
import shutil
from pathlib import Path

from afc import plan
from afc.config import afc_home, afc_root
from afc.registry import load_registry

NAMES = ("plan",)
NO_PLAN = "This project has no master plan yet. A health check repair adds one."
ARCHIVE_INDEX = "# Archive\n\n| ID | Title | Done | Spec |\n|---|---|---|---|\n"


def register(sub) -> None:
    p = sub.add_parser("plan", help="show or move the master plan")
    p.set_defaults(handler=cmd_plan)
    psub = p.add_subparsers(dest="plan_command")
    q = psub.add_parser("add", help="add a spec to Next")
    q.add_argument("title")
    q.add_argument("--size", choices=("S", "M", "L"), default="M")
    q.set_defaults(handler=cmd_add)
    q = psub.add_parser("start", help="move a spec from Next to Now")
    q.add_argument("id")
    q.set_defaults(handler=cmd_start)
    q = psub.add_parser("done", help="finish the spec in Now and archive it")
    q.add_argument("id")
    q.set_defaults(handler=cmd_done)


def _cli():
    from afc import cli  # late import: afc.cli imports this module

    return cli


def _error(message: str) -> Exception:
    return _cli().CliError(message)


def _load() -> tuple[Path, Path, str]:
    """(workspace, master-plan path, master text) of the active project."""
    from afc.cli import NO_ACTIVE

    project = load_registry(afc_home()).active()
    if project is None:
        raise _error(NO_ACTIVE)
    ws = Path(project.workspace_path)
    path = ws / "plan" / plan.MASTER
    if not path.is_file():
        raise _error(NO_PLAN)
    return ws, path, path.read_text(encoding="utf-8")


def _spec_path(ws: Path, row: list[str]) -> Path:
    m = re.search(r"\(([^)]*)\)", row[3] if len(row) > 3 else "")
    return ws / "plan" / (m.group(1) if m else "")


def _find(text: str, sid: str) -> tuple[str, list[str]]:
    for section in ("Now", "Next", "Done"):
        for row in plan.read_rows(text, section):
            if row and row[0] == sid:
                return section, row
    raise _error(f"No spec {sid} in the master plan.")


def _read_spec(ws: Path, sid: str, row: list[str]) -> tuple[Path, str]:
    path = _spec_path(ws, row)
    if not path.is_file():
        raise _error(f"The spec file for {sid} is missing: {path}")
    return path, path.read_text(encoding="utf-8")


def _goal(text: str) -> str:
    lines = text.split("\n")
    try:
        start, end = plan._section_span(lines, "Goal")
    except ValueError:
        return ""
    return next((ln.strip() for ln in lines[start:end] if ln.strip()), "")


def cmd_plan(args: argparse.Namespace) -> dict:
    ws, _, text = _load()
    now_rows = plan.read_rows(text, "Now")
    now = None
    if now_rows:
        row = now_rows[0]
        _, spec_text = _read_spec(ws, row[0], row)
        open_ = plan.open_slices(spec_text)
        now = {"id": row[0], "title": row[1], "spec": str(_spec_path(ws, row)), "next_slice": open_[0] if open_ else None}
    nxt = [{"id": r[0], "title": r[1], "size": r[2]} for r in plan.read_rows(text, "Next")[:2]]
    return {"goal": _goal(text), "now": now, "next": nxt, "done_count": len(plan.read_rows(text, "Done"))}


def cmd_add(args: argparse.Namespace) -> dict:
    ws, path, text = _load()
    title = plan.cell(args.title)
    if not title:
        raise _error("Give the spec a title.")
    plan_dir = ws / "plan"
    (plan_dir / "specs").mkdir(parents=True, exist_ok=True)
    (plan_dir / "archive").mkdir(parents=True, exist_ok=True)
    sid = plan.next_id(ws)
    name = f"{sid}-{plan.slugify(title)}.md"
    template = (afc_root() / "templates" / "workspace" / "spec.md").read_text(encoding="utf-8")
    body = template.replace("{id}", sid).replace("{title}", title).replace("{size}", args.size)
    target = plan_dir / "specs" / name
    new = plan.write_rows(text, "Next", plan.read_rows(text, "Next") + [[sid, title, args.size, f"[spec](specs/{name})"]])
    new = plan.log(new, _cli()._today(), f"{sid} added")
    target.write_text(body, encoding="utf-8")
    try:
        path.write_text(new, encoding="utf-8")
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {"created": sid, "title": title, "size": args.size, "spec": str(target)}


def cmd_start(args: argparse.Namespace) -> dict:
    ws, path, text = _load()
    sid = args.id
    section, row = _find(text, sid)
    now_rows = plan.read_rows(text, "Now")
    if now_rows:
        raise _error(f"{now_rows[0][0]} is still in progress. Finish it first.")
    if section != "Next":
        raise _error(f"{sid} isn't waiting in Next.")
    spec_path, spec_text = _read_spec(ws, sid, row)
    today = _cli()._today()
    new = plan.write_rows(text, "Next", [r for r in plan.read_rows(text, "Next") if r[0] != sid])
    new = plan.write_rows(new, "Now", [[sid, row[1], row[2], row[3], today]])
    new = plan.log(new, today, f"{sid} started")
    spec_path.write_text(plan.set_header(spec_text, status="in progress", started=today), encoding="utf-8")
    try:
        path.write_text(new, encoding="utf-8")
    except BaseException:
        spec_path.write_text(spec_text, encoding="utf-8")
        raise
    open_ = plan.open_slices(plan.set_header(spec_text, status="in progress", started=today))
    return {"started": sid, "next_slice": open_[0] if open_ else None}


def _shipped(spec_text: str, line: str) -> str:
    lines = spec_text.split("\n")
    try:
        start, end = plan._section_span(lines, "Shipped")
    except ValueError:
        return spec_text.rstrip("\n") + f"\n\n## Shipped\n\n{line}\n"
    return "\n".join(lines[:start] + ["", line, ""] + lines[end:])


def _archive_index(current: str, row: list[str]) -> str:
    text = current if current.strip() else ARCHIVE_INDEX
    new = "| " + " | ".join(plan.cell(c) for c in row) + " |"
    lines = text.split("\n")
    table = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("|")]
    if len(table) < 2:
        return text.rstrip("\n") + "\n\n" + ARCHIVE_INDEX + new + "\n"
    lines.insert(table[1] + 1, new)
    return "\n".join(lines)


def cmd_done(args: argparse.Namespace) -> dict:
    ws, path, text = _load()
    sid = args.id
    section, row = _find(text, sid)
    if section != "Now":
        raise _error(f"{sid} isn't in progress.")
    spec_path, spec_text = _read_spec(ws, sid, row)
    slices = plan.all_slices(spec_text)
    open_ = plan.open_slices(spec_text)
    if open_:
        raise _error(f"{sid} still has {len(open_)} open slice(s), starting with: {open_[0]}")
    if not slices:
        raise _error(f"{sid} has no slices yet.")
    today = _cli()._today()
    name = spec_path.name
    archive = ws / "plan" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    target = archive / name
    index_path = archive / "index.md"
    old_index = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    done_row = [sid, row[1], today]
    new = plan.write_rows(text, "Now", [])
    new = plan.write_rows(new, "Done", [done_row + [f"[{sid}](archive/{name})"]] + plan.read_rows(new, "Done"))
    new = plan.log(new, today, f"{sid} done")
    body = plan.set_header(spec_text, status="done", done=today)
    body = _shipped(body, f"Shipped {today}. Slices: {len(slices)}.")
    shutil.move(str(spec_path), str(target))
    try:
        target.write_text(body, encoding="utf-8")
        index_path.write_text(_archive_index(old_index or "", done_row + [name]), encoding="utf-8")
        path.write_text(new, encoding="utf-8")
        plan.compact(ws)
    except BaseException:
        path.write_text(text, encoding="utf-8")
        if old_index is None:
            index_path.unlink(missing_ok=True)
        else:
            index_path.write_text(old_index, encoding="utf-8")
        shutil.move(str(target), str(spec_path))
        spec_path.write_text(spec_text, encoding="utf-8")
        raise
    nxt = plan.read_rows(path.read_text(encoding="utf-8"), "Next")
    suggest = {"id": nxt[0][0], "title": nxt[0][1]} if nxt else None
    return {"done": sid, "archived": str(target), "suggest_next": suggest}
