"""Plan commands: plan, plan add|goal|rename|drop|move|set|start|reopen|done.

Registered into the main parser by afc.cli through register(). They move a spec from
Next to Now to Done in the master plan and keep its file in specs/ or the archive.
In maintenance mode they manage Flight Control's own plan (docs/master-plan.md); otherwise the
active project's. Each handler returns one JSON-able dict, like every other Flight Control command.
"""

import argparse
import re
import shutil
import subprocess
from pathlib import Path

from afc import plan
from afc.config import afc_home, afc_root, current_session, maintain_enabled
from afc.registry import load_registry

NAMES = ("plan",)
NO_PLAN = "This project has no master plan yet. A health check repair adds one."
NO_FC_PLAN = "Flight Control has no master plan at docs/master-plan.md."
UNREADABLE = "unreadable"  # slice lines without `- [ ]`, which `plan` cannot see
ARCHIVE_INDEX ="# Archive\n\n| ID | Title | Done | Spec |\n|---|---|---|---|\n"


def register(sub) -> None:
    p = sub.add_parser("plan", help="show or move the master plan")
    p.set_defaults(handler=cmd_plan)
    psub = p.add_subparsers(dest="plan_command")
    q = psub.add_parser("add", help="add a spec to Next")
    q.add_argument("title")
    q.add_argument("--size", choices=("S", "M", "L"), default="M")
    q.set_defaults(handler=cmd_add)
    q = psub.add_parser("goal", help="set the master plan's goal")
    q.add_argument("text")
    q.set_defaults(handler=cmd_goal)
    q = psub.add_parser("rename", help="give a spec a new title (file, row and heading change together)")
    q.add_argument("id")
    q.add_argument("title")
    q.set_defaults(handler=cmd_rename)
    q = psub.add_parser("drop", help="archive a waiting spec as dropped (never deleted)")
    q.add_argument("id")
    q.set_defaults(handler=cmd_drop)
    q = psub.add_parser("move", help="change a waiting spec's place in Next")
    q.add_argument("id")
    q.add_argument("--to", type=int, required=True, help="position in Next, 1 is first")
    q.set_defaults(handler=cmd_move)
    q = psub.add_parser("set", help="change a waiting or running spec's size or what it waits for")
    q.add_argument("id")
    q.add_argument("--size", choices=("S", "M", "L"))
    q.add_argument("--depends", help="the spec that must be done first (a comma list, or none to clear)")
    q.set_defaults(handler=cmd_set)
    q = psub.add_parser("start", help="move a spec from Next to Now")
    q.add_argument("id")
    q.set_defaults(handler=cmd_start)
    q = psub.add_parser("reopen", help="bring a finished spec back to Next")
    q.add_argument("id")
    q.set_defaults(handler=cmd_reopen)
    q = psub.add_parser("done", help="finish the spec in Now and archive it")
    q.add_argument("id")
    q.add_argument("--outcome", nargs=2, metavar=("RESULT", "WHY"),
                   help='what it reached: met, partly or not-met, then the number or reason')
    q.set_defaults(handler=cmd_done)
    q = psub.add_parser("score", help="update one Scoreboard measure and log it")
    q.add_argument("name")
    q.add_argument("value")
    q.add_argument("--keep-before", action="store_true", help="move the old value to Before")
    q.set_defaults(handler=cmd_score)


def _cli():
    from afc import cli  # late import: afc.cli imports this module

    return cli


def _error(message: str) -> Exception:
    return _cli().CliError(message)


def _plan_root() -> Path:
    """Flight Control's one plan lives in the main checkout (first `git worktree list` entry), so a
    worktree or fork reads and writes it through there. Falls back to this folder."""
    here = afc_root()
    try:
        out = subprocess.run(["git", "-C", str(here), "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, timeout=10, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return here
    first = out.split("\n\n")[0]
    for line in first.split("\n"):
        if line.startswith("worktree "):
            main = Path(line[len("worktree "):])
            return main if (main / "docs" / "master-plan.md").is_file() else here
    return here


def _guard_main(main: Path) -> None:
    """Refuse a write through a worktree when the main checkout is not on dev or has plan edits."""
    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(main), *a], capture_output=True, text=True).stdout.strip()

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "dev":
        raise _error(f"The master plan lives on dev in {main}, but that folder is on {branch or 'another branch'}. "
                     "Switch it to dev first.")
    if git("status", "--short", "--", "docs/master-plan.md", "docs/specs"):
        raise _error(f"The master plan in {main} has changes that are not committed yet. "
                     "Commit or set them aside there first, so this change does not mix with them.")


def _load(write: bool = False) -> tuple[plan.Space, str, str]:
    """(plan space, whose plan, master text): Flight Control's own in maintenance mode, else the
    active project's."""
    from afc.cli import NO_ACTIVE

    home = afc_home()
    if maintain_enabled(home, current_session()):
        root = _plan_root()
        if write and root != afc_root():
            _guard_main(root)
        space, owner, missing = plan.flight_control_space(root), "Flight Control", NO_FC_PLAN
    else:
        project = load_registry(home).active()
        if project is None:
            raise _error(NO_ACTIVE)
        space = plan.project_space(Path(project.workspace_path))
        owner, missing = project.name, NO_PLAN
    if not space.master.is_file():
        raise _error(missing)
    return space, owner, space.master.read_text(encoding="utf-8")


def _spec_path(space: plan.Space, row: list[str]) -> Path:
    m = re.search(r"\(([^)]*)\)", row[3] if len(row) > 3 else "")
    return space.base / (m.group(1) if m else "")


def _missing(space: plan.Space, sid: str) -> str:
    """Why a spec ID isn't here; an ID from the other numbering gets a plain hint."""
    if space.prefix == "FC" and sid.startswith("S-"):
        return (f"{sid} is a project spec, but maintenance mode is on, so only Flight Control's "
                "own plan (FC-…) is in use. Turn maintenance mode off with /afc mm off.")
    if space.prefix == "S" and sid.startswith("FC-"):
        return f"{sid} is a Flight Control spec. Turn on maintenance mode first (/afc mm)."
    return f"No spec {sid} in the master plan."


def _find(space: plan.Space, text: str, sid: str) -> tuple[str, list[str]]:
    for section in ("Now", "Next", "Done"):
        for row in plan.read_rows(text, section):
            if row and row[0] == sid:
                return section, row
    raise _error(_missing(space, sid))


def _read_spec(space: plan.Space, sid: str, row: list[str]) -> tuple[Path, str]:
    path = _spec_path(space, row)
    if not path.is_file():
        raise _error(f"The spec file for {sid} is missing: {path}")
    return path, path.read_text(encoding="utf-8")


def _goal(text: str) -> str:
    lines = text.split("\n")
    try:
        start, end = plan._section_span(lines, "Goal")
    except ValueError:
        return ""
    para: list[str] = []
    for ln in lines[start:end]:
        if ln.strip():
            para.append(ln.strip())
        elif para:
            break
    return " ".join(para)  # the first paragraph, which may wrap over several lines


def _ready(space: plan.Space, row: list[str]) -> dict:
    """Is the spec ready for build, and if not what is missing (every plan, not only Flight Control's)."""
    path = _spec_path(space, row)
    if not path.is_file():
        return {"ready": False, "missing": ["the spec file is missing"]}
    return plan.readiness(path.read_text(encoding="utf-8"), space.prefix == "FC")


def cmd_plan(args: argparse.Namespace) -> dict:
    home = afc_home()
    if not maintain_enabled(home, current_session()) and load_registry(home).active() is None:
        return {"for": None, "active": None, "now": None, "next": [], "message": "No active project, so there is no plan to show."}
    space, owner, text = _load()
    now_rows = plan.read_rows(text, "Now")
    now = None
    if now_rows:
        row = now_rows[0]
        _, spec_text = _read_spec(space, row[0], row)
        open_ = plan.open_slices(spec_text)
        now = {"id": row[0], "title": row[1], "spec": str(_spec_path(space, row)), "next_slice": open_[0] if open_ else None}
        if plan.unreadable_slices(spec_text):
            now["slices"] = UNREADABLE
    nxt = [{"id": r[0], "title": r[1], "size": r[2], **_ready(space, r)} for r in plan.read_rows(text, "Next")[:2]]
    return {"for": owner, "goal": _goal(text), "now": now, "next": nxt,
            "done_count": len(plan.read_rows(text, "Done"))}


def cmd_add(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    path = space.master
    title = plan.cell(args.title)
    if not title:
        raise _error("Give the spec a title.")
    space.specs.mkdir(parents=True, exist_ok=True)
    space.archive_dir.mkdir(parents=True, exist_ok=True)
    sid = plan.next_id(space)
    name = f"{sid}-{plan.slugify(title)}.md"
    template = (afc_root() / "templates" / "workspace" / "spec.md").read_text(encoding="utf-8")
    body = template.replace("{id}", sid).replace("{title}", title).replace("{size}", args.size)
    target = space.specs / name
    new = plan.write_rows(text, "Next", plan.read_rows(text, "Next") + [[sid, title, args.size, f"[spec](specs/{name})"]])
    new = plan.log(new, _cli()._today(), f"{sid} added")
    target.write_text(body, encoding="utf-8")
    try:
        path.write_text(new, encoding="utf-8")
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {"created": sid, "title": title, "size": args.size, "spec": str(target)}


def cmd_goal(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    goal = " ".join(args.text.split())
    if not goal:
        raise _error("Give the goal as one line of text.")
    try:
        new = plan.set_goal(text, goal)
    except ValueError as exc:
        raise _error(str(exc)) from None
    space.master.write_text(plan.log(new, _cli()._today(), "Goal set"), encoding="utf-8")
    return {"goal": goal}


def cmd_rename(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    sid = args.id
    title = plan.cell(args.title)
    if not title:
        raise _error("Give the spec a title.")
    section, row = _find(space, text, sid)
    if section == "Done":
        raise _error(f"{sid} is finished, so it can't be renamed.")
    old_path, spec_text = _read_spec(space, sid, row)
    name = f"{sid}-{plan.slugify(title)}.md"
    new_path = old_path.with_name(name)
    if new_path != old_path and new_path.exists():
        raise _error(f"There is already a file called {name}.")
    row = [row[0], title, row[2], f"[spec](specs/{name})", *row[4:]]
    rows = [row if r[0] == sid else r for r in plan.read_rows(text, section)]
    new = plan.log(plan.write_rows(text, section, rows), _cli()._today(), f"{sid} renamed to {title}")
    body = re.sub(r"\A# [^\n]*", f"# {sid} — {title}", spec_text, count=1)
    old_path.rename(new_path)
    try:
        new_path.write_text(body, encoding="utf-8")
        space.master.write_text(new, encoding="utf-8")
    except BaseException:
        new_path.write_text(spec_text, encoding="utf-8")
        new_path.rename(old_path)
        raise
    return {"renamed": sid, "title": title, "spec": str(new_path)}


def _is_done(text: str, sid: str) -> bool:
    """Is sid a finished spec in Done? A dropped one, or an ID the plan doesn't have, is not."""
    for row in plan.read_rows(text, "Done"):
        if row and row[0] == sid:
            return not row[1].endswith("(dropped)")
    return False


def cmd_set(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    sid = args.id
    if args.size is None and args.depends is None:
        raise _error("Say what to change: --size S, M or L, and/or --depends <spec id> (or none).")
    section, row = _find(space, text, sid)
    if section == "Done":
        raise _error(f"{sid} is finished, so it can't be changed. Reopen it first.")
    spec_path, spec_text = _read_spec(space, sid, row)
    fields: dict = {}
    events: list[str] = []
    if args.size is not None:
        fields["size"] = args.size
        events.append(f"size set to {args.size}")
    deps: list[str] | None = None
    if args.depends is not None:
        raw = [d.strip() for d in re.split(r"[,\s]+", args.depends) if d.strip()]
        deps = [] if [d.lower() for d in raw] == ["none"] else raw
        for dep in deps:
            if dep == sid:
                raise _error(f"{sid} can't wait for itself.")
            _find(space, text, dep)  # a plain error when the plan doesn't have it
        fields["depends"] = ", ".join(deps)
        events.append(f"waits for {', '.join(deps)}" if deps else "waits for nothing")
    rows = [[r[0], r[1], args.size or r[2], *r[3:]] if r[0] == sid else r for r in plan.read_rows(text, section)]
    new = plan.log(plan.write_rows(text, section, rows), _cli()._today(), f"{sid} " + " and ".join(events))
    spec_path.write_text(plan.set_header(spec_text, **fields), encoding="utf-8")
    try:
        space.master.write_text(new, encoding="utf-8")
    except BaseException:
        spec_path.write_text(spec_text, encoding="utf-8")
        raise
    out = {"changed": sid, "size": args.size or row[2]}
    out["depends"] = deps if deps is not None else plan.depends(spec_text)
    return out


def cmd_start(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    path = space.master
    sid = args.id
    section, row = _find(space, text, sid)
    now_rows = plan.read_rows(text, "Now")
    if now_rows:
        raise _error(f"{now_rows[0][0]} is still in progress. Finish it first.")
    if section != "Next":
        raise _error(f"{sid} isn't waiting in Next.")
    spec_path, spec_text = _read_spec(space, sid, row)
    for dep in plan.depends(spec_text):
        if not _is_done(text, dep):
            raise _error(f"{sid} waits for {dep}, which is not done yet. Finish {dep} first, "
                         f"or run: plan set {sid} --depends none")
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
    started = {"started": sid, "next_slice": open_[0] if open_ else None}
    if plan.unreadable_slices(spec_text):
        started["slices"] = UNREADABLE
    return started


def _shipped(spec_text: str, line: str) -> str:
    lines = spec_text.split("\n")
    try:
        start, end = plan._section_span(lines, "Shipped")
    except ValueError:
        return spec_text.rstrip("\n") + f"\n\n## Shipped\n\n{line}\n"
    return "\n".join(lines[:start] + ["", line, ""] + lines[end:])


def _criteria_line(spec_text: str) -> str:
    numbered = plan.criteria(spec_text)
    if not numbered:
        return "Criteria: not numbered."
    named = {c for _, label in plan.all_slices(spec_text) for c in plan.proofs(label)}
    proven = sum(1 for c in numbered if c in named)
    return f"Criteria: {proven} of {len(numbered)} proven."


def _archive_index(current: str, row: list[str]) -> str:
    text = current if current.strip() else ARCHIVE_INDEX
    new = "| " + " | ".join(plan.cell(c) for c in row) + " |"
    lines = text.split("\n")
    table = [i for i, ln in enumerate(lines) if ln.lstrip().startswith("|")]
    if len(table) < 2:
        return text.rstrip("\n") + "\n\n" + ARCHIVE_INDEX + new + "\n"
    lines.insert(table[1] + 1, new)
    return "\n".join(lines)


def _waiting(space: plan.Space, text: str, sid: str, verb: str) -> tuple[list[str], list[list[str]]]:
    """The Next row for sid and all Next rows; a spec in progress or finished can't be dropped or moved."""
    section, row = _find(space, text, sid)
    if section == "Now":
        extra = " Finish it or rename it." if verb == "dropped" else ""
        raise _error(f"{sid} is in progress, so it can't be {verb}.{extra}")
    if section == "Done":
        raise _error(f"{sid} is finished, so it can't be {verb}.")
    return row, plan.read_rows(text, "Next")


def cmd_drop(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    sid = args.id
    row, waiting = _waiting(space, text, sid, "dropped")
    spec_path, spec_text = _read_spec(space, sid, row)
    today = _cli()._today()
    name = spec_path.name
    target = space.archive_dir / name
    space.archive_dir.mkdir(parents=True, exist_ok=True)
    index_path = space.archive_dir / "index.md"
    old_index = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    done_row = [sid, f"{row[1]} (dropped)", today]
    new = plan.write_rows(text, "Next", [r for r in waiting if r[0] != sid])
    new = plan.write_rows(new, "Done", [done_row + [f"[{sid}]({space.archive}/{name})", "", "dropped"]] + plan.read_rows(new, "Done"))
    new = plan.log(new, today, f"{sid} dropped")
    shutil.move(str(spec_path), str(target))
    try:
        target.write_text(plan.set_header(spec_text, status="dropped", done=today), encoding="utf-8")
        index_path.write_text(_archive_index(old_index or "", done_row + [name]), encoding="utf-8")
        space.master.write_text(new, encoding="utf-8")
    except BaseException:
        if old_index is None:
            index_path.unlink(missing_ok=True)
        else:
            index_path.write_text(old_index, encoding="utf-8")
        shutil.move(str(target), str(spec_path))
        spec_path.write_text(spec_text, encoding="utf-8")
        raise
    return {"dropped": sid, "archived": str(target)}


def cmd_move(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    sid = args.id
    row, waiting = _waiting(space, text, sid, "moved")
    if not 1 <= args.to <= len(waiting):
        raise _error(f"Pick a position from 1 to {len(waiting)}.")
    waiting = [r for r in waiting if r[0] != sid]
    waiting.insert(args.to - 1, row)
    new = plan.log(plan.write_rows(text, "Next", waiting), _cli()._today(), f"{sid} moved to position {args.to}")
    space.master.write_text(new, encoding="utf-8")
    return {"moved": sid, "position": args.to, "next": [r[0] for r in waiting]}


def _without_changelog_entry(changelog: str, sid: str) -> str:
    """The changelog with the entry for sid taken out (one entry per spec)."""
    lines = changelog.split("\n")
    out: list[str] = []
    skipping = False
    for ln in lines:
        if ln.startswith("## "):
            skipping = bool(re.match(rf"## \S+ — {re.escape(sid)}\b", ln))
        if not skipping:
            out.append(ln)
    return "\n".join(out)


def cmd_reopen(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    sid = args.id
    section, row = _find(space, text, sid)
    if section != "Done":
        raise _error(f"{sid} isn't finished, so there is nothing to reopen.")
    archived, spec_text = _read_spec(space, sid, row)
    name = archived.name
    target = space.specs / name
    if target.exists():
        raise _error(f"There is already a file called {name} in specs, so {sid} can't come back.")
    today = _cli()._today()
    title = re.sub(r"\s*\(dropped\)$", "", row[1])
    size = plan.header_size(spec_text) or "M"
    new = plan.write_rows(text, "Done", [r for r in plan.read_rows(text, "Done") if r[0] != sid])
    new = plan.write_rows(new, "Next", [[sid, title, size, f"[spec](specs/{name})"]] + plan.read_rows(new, "Next"))
    new = plan.log(new, today, f"{sid} reopened")
    body = plan.set_header(spec_text, status="next", started="-", done="-")
    index_path = space.archive_dir / "index.md"
    old_index = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    changelog = (space.base if space.prefix == "FC" else space.base.parent) / "changelog.md"
    old_changelog = changelog.read_text(encoding="utf-8") if changelog.is_file() else None
    space.specs.mkdir(parents=True, exist_ok=True)
    shutil.move(str(archived), str(target))
    try:
        target.write_text(body, encoding="utf-8")
        if old_index is not None:
            kept = [ln for ln in old_index.split("\n")
                    if not (ln.lstrip().startswith("|") and plan._split_row(ln)[:1] == [sid])]
            index_path.write_text("\n".join(kept), encoding="utf-8")
        if old_changelog is not None:
            changelog.write_text(_without_changelog_entry(old_changelog, sid), encoding="utf-8")
        space.master.write_text(new, encoding="utf-8")
    except BaseException:
        if old_changelog is not None:
            changelog.write_text(old_changelog, encoding="utf-8")
        if old_index is not None:
            index_path.write_text(old_index, encoding="utf-8")
        shutil.move(str(target), str(archived))
        archived.write_text(spec_text, encoding="utf-8")
        raise
    return {"reopened": sid, "spec": str(target)}


OUTCOMES = {"met": "met", "partly": "partly", "not-met": "not met"}


def _outcome_cell(args: argparse.Namespace) -> str:
    given = getattr(args, "outcome", None)
    if not given:
        return ""
    result, why = given
    if result not in OUTCOMES:
        raise _error("The result must be met, partly or not-met.")
    why = why.strip()
    return OUTCOMES[result] + (f": {why}" if why else "")


def cmd_done(args: argparse.Namespace) -> dict:
    outcome = _outcome_cell(args)
    space, _, text = _load(write=True)
    path = space.master
    sid = args.id
    section, row = _find(space, text, sid)
    if section != "Now":
        raise _error(f"{sid} isn't in progress.")
    spec_path, spec_text = _read_spec(space, sid, row)
    from afc import cli_ship, ship

    gate = cli_ship.run_gate(spec_text)
    if not gate["ready"]:
        lines = "\n".join(f"- {m}" for m in gate["missing"])
        raise _error(f"{sid} is not ready to finish yet:\n{lines}\nNext: {gate['next']}")
    slices = plan.all_slices(spec_text)
    today = _cli()._today()
    name = spec_path.name
    archive = space.archive_dir
    archive.mkdir(parents=True, exist_ok=True)
    target = archive / name
    index_path = archive / "index.md"
    old_index = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    done_row = [sid, row[1], today]
    new = plan.write_rows(text, "Now", [])
    new = plan.write_rows(new, "Done", [done_row + [f"[{sid}]({space.archive}/{name})", "", outcome]] + plan.read_rows(new, "Done"))
    new = plan.log(new, today, f"{sid} done")
    body = plan.set_header(spec_text, status="done", done=today)
    body = _shipped(body, f"Shipped {today}. Slices: {len(slices)}. {_criteria_line(spec_text)}")
    changelog = (space.base if space.prefix == "FC" else space.base.parent) / "changelog.md"
    old_changelog = changelog.read_text(encoding="utf-8") if changelog.is_file() else None
    entry = ship.changelog_entry(spec_text, sid, row[1], today)
    shutil.move(str(spec_path), str(target))
    try:
        target.write_text(body, encoding="utf-8")
        index_path.write_text(_archive_index(old_index or "", done_row + [name]), encoding="utf-8")
        changelog.write_text(ship.add_to_changelog(old_changelog or "", entry), encoding="utf-8")
        path.write_text(new, encoding="utf-8")
        plan.compact(space)
    except BaseException:
        path.write_text(text, encoding="utf-8")
        if old_changelog is None:
            changelog.unlink(missing_ok=True)
        else:
            changelog.write_text(old_changelog, encoding="utf-8")
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


def cmd_score(args: argparse.Namespace) -> dict:
    space, _, text = _load(write=True)
    try:
        new, old = plan.set_score(text, args.name, args.value.strip())
        if args.keep_before:
            new, _ = plan.set_score(text, args.name, args.value.strip(), keep_before=True)
    except ValueError as e:
        raise _error(str(e))
    note = f"Scoreboard: {args.name.strip()} {old} -> {args.value.strip()}" + (" (old value kept as before)" if args.keep_before else "")
    new = plan.log(new, _cli()._today(), note)
    space.master.write_text(new, encoding="utf-8")
    return {"scored": args.name.strip(), "now": args.value.strip(), "was": old, "kept_before": bool(args.keep_before)}
