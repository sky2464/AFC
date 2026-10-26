"""Health commands: check, repair and relocate.

Registered into the main parser by afc.cli through register(). check only reads; repair fixes
what needs no decision (folder access, missing or leftover workspaces); relocate points a project
at its code folder after the user moved it. Nothing is ever deleted.
"""

import argparse
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from afc import addons, tools
from afc.config import afc_home, current_session, maintain_enabled
from afc.registry import load_registry, save_registry
from afc.session_dirs import (GrantError, block_addons, blocked_addons, check_settings, drop_dirs, grant_dirs,
                              granted_now, settings_path)
from afc.undo import Undo
from afc.workspace import create_workspace

NAMES = ("check", "repair", "relocate")
ACCESS = ("stale_access", "gone_access", "missing_access", "foreign_access")
ADDONS = ("addon_not_allowed", "addon_unblock")
PLAN_KINDS = ("plan_all_ticked_in_now", "plan_built_in_next", "plan_copy_differs", "plan_two_in_now",
              "plan_no_spec_file", "plan_status_mismatch", "plan_archive_not_indexed", "plan_table_broken",
              "plan_uncommitted")
PLAN_CLOSES = ("plan_all_ticked_in_now", "plan_built_in_next", "plan_copy_differs")  # closing a spec in the plan
PLAN_WHY_LEFT = {
    "plan_two_in_now": "which spec stays in progress is your call",
    "plan_no_spec_file": "only you know whether the spec was dropped or the file moved",
    "plan_status_mismatch": "either the plan or the spec header is right, and that needs your decision",
    "plan_table_broken": "a row with the wrong number of cells could lose text if it were guessed at",
    "plan_uncommitted": "committing is yours to approve",
}
PLAN_MAX_LINES = 150
PLAN_MAX_LOG = 30
ROOT_BRANCHES = ("main", "dev")
GIT_TIMEOUT = 3  # seconds: the welcome runs this check, so it must stay quick


def register(sub) -> None:
    p = sub.add_parser("check", help="find problems across all projects (changes nothing)")
    p.set_defaults(handler=cmd_check)

    p = sub.add_parser("repair", help="fix the problems that need no decision")
    p.set_defaults(handler=cmd_repair)

    p = sub.add_parser("relocate", help="point a project at its code folder's new place")
    p.add_argument("name")
    p.add_argument("--path", required=True)
    p.set_defaults(handler=cmd_relocate)


def _cli():
    from afc import cli  # late import: afc.cli imports this module

    return cli


def cmd_check(args: argparse.Namespace) -> dict:
    problems = find_problems(afc_home())
    result = {"ok": not problems, "problems": problems}
    note = root_git_note()
    if note:
        result["note"] = note
    return result


def cmd_repair(args: argparse.Namespace) -> dict:
    """Recreate missing workspaces, put leftover ones away, and set folder access to exactly the
    active project's folders, dropping entries for folders that no longer exist."""
    cli = _cli()
    home = afc_home()
    reg = load_registry(home)
    repaired: list[str] = []
    for p in find_problems(home):
        if p["kind"] == "workspace_missing" and p["fixable"]:
            create_workspace(home, p["project"])
            repaired.append(f"Recreated the empty workspace for {p['project']}.")
        elif p["kind"] == "orphan_workspace":
            from afc.cli_projects import _removed_dir

            dest = _removed_dir(home, Path(p["path"]).name)
            dest.mkdir(parents=True)
            shutil.move(p["path"], str(dest / "workspace"))
            repaired.append(f"Put the leftover workspace {p['path']} away in {dest}.")
        elif p["kind"] == "stale_maintain":
            (home / "maintain").unlink(missing_ok=True)
            repaired.append("Removed the old global maintenance switch.")
        elif p["kind"] == "test_copy_behind" and p["fixable"]:
            # Changing git in the A-FC folder needs maintenance mode, as it does when typed. The copy
            # is already detached and clean, so reset moves it without a new detach.
            if not maintain_enabled(home, current_session()):
                repaired.append("This test copy is behind dev; bringing it up to date changes Flight "
                                "Control's own folder, so it needs maintenance mode (/afc mm).")
            elif _git(cli.afc_root(), "reset", "--hard", "dev") is not None:
                repaired.append("Brought this test copy up to date with dev.")
        elif p["kind"] == "root_detached" and p["fixable"]:
            if _git(cli.afc_root(), "switch", "main") is not None:
                repaired.append("Put Flight Control's own copy back on main.")
        elif p["kind"] == "old_plan_format":
            _upgrade_plan(Path(p["path"]))
            repaired.append(f"Upgraded {p['project']} to a master plan.")
        elif p["kind"] == "decisions_no_log":
            path = Path(p["path"])
            path.write_text(path.read_text(encoding="utf-8").rstrip("\n") + "\n" + LOG_SECTION, encoding="utf-8")
            repaired.append(f"Added a Log section to {p['project']}'s decisions.")
    repaired += _repair_plan(home, [p for p in find_problems(home) if p["kind"] in PLAN_KINDS])
    access = [p for p in find_problems(home) if p["kind"] in ACCESS]
    if access:
        undo = cli._settings_undo()
        undo.save_settings()
        try:
            grant_dirs(cli.afc_root(), _wanted(reg))
            drop_dirs(cli.afc_root(), [p["path"] for p in access if p["kind"] in ("gone_access", "foreign_access")])
        except BaseException:
            undo.rollback()
            raise
        repaired.append("Folder access now matches the active project.")
    if any(p["kind"] == "tools_out_of_sync" for p in find_problems(home)):
        undo = cli._settings_undo()
        undo.save_settings()
        undo.on_rollback(tools.snapshot(cli.afc_root()))
        try:
            active = reg.active()
            if active is not None and Path(active.workspace_path).is_dir():
                tools.swap_in(cli.afc_root(), Path(active.workspace_path))
            else:
                tools.clear(cli.afc_root())
        except tools.ToolsError as exc:
            undo.rollback()
            raise cli.CliError(str(exc))
        except BaseException:
            undo.rollback()
            raise
        repaired.append("Project tools now match the active project; this applies from the next start.")
    off, on = switch_addons(cli.afc_root(), [p for p in find_problems(home) if p["kind"] in ADDONS])
    if off:
        repaired.append(f"Switched off {off} add-on{'s' if off > 1 else ''} in Flight Control sessions; "
                        "this applies from the next start.")
    if on:
        repaired.append("Switched back on add-ons that are now allowed; this applies from the next start.")
    return {"repaired": repaired, "left": find_problems(home)}


def plan_problems(space, owner: str = "") -> list[dict]:
    """A master plan gone wrong, Flight Control's own (owner "") or a project's (owner = its name).

    Found everywhere: two rows in Now, a Now or Next row whose spec file is gone, a spec header that
    disagrees with its section, an archived spec missing from the archive index, a table row with the
    wrong number of cells. Flight Control's own plan also gets: a Now row with every slice ticked, a
    built spec still in Next, a worktree copy that differs, and uncommitted edits (not while a build
    has an open slice). Only a missing archive index entry is fixable by repair. Reads only."""
    from afc import cli_plan, plan

    master = space.master
    if not master.is_file():
        return []
    own = space.prefix == "FC"
    whose = "Flight Control's plan" if own else f"{owner}'s plan"
    text = master.read_text(encoding="utf-8")
    found: list[dict] = []

    def add(kind: str, path: Path, detail: str, fixable: bool = False) -> None:
        found.append(_problem(kind, str(path), fixable, detail=f"{whose}: {detail}", project="" if own else owner))

    # Tables first; a row with the wrong number of cells is reported and left out of the checks below.
    rows: dict[str, list[list[str]]] = {}
    for section in ("Now", "Next", "Done", "Update log"):
        try:
            cells = _table_widths(text, section)
        except ValueError:
            add("plan_table_broken", master, f"the {section} section or its table is missing.")
            continue
        header, body = cells
        bad = [c for c in body if c != header]
        if bad:
            add("plan_table_broken", master,
                f"the {section} table has {len(bad)} row{'s' if len(bad) > 1 else ''} with the wrong "
                f"number of cells (it should have {header}).")
        rows[section] = [r for r in plan.read_rows(text, section) if len(r) == header]
    now, nxt = rows.get("Now", []), rows.get("Next", [])
    if len(now) > 1:
        add("plan_two_in_now", master,
            f"{len(now)} specs are in Now ({', '.join(r[0] for r in now)}); only one can be in progress.")
    expected = {"Now": "in progress", "Next": "next"}
    for section, section_rows in (("Now", now), ("Next", nxt)):
        for row in section_rows:
            spec = cli_plan._spec_path(space, row)
            if not spec.is_file():
                add("plan_no_spec_file", master, f"{row[0]} is in {section} but its spec file is missing.")
                continue
            spec_text = spec.read_text(encoding="utf-8")
            status = _header_status(spec_text)
            if status and status != expected[section]:
                add("plan_status_mismatch", spec,
                    f"{row[0]} is in {section} but its spec says \"{status}\".")
            slices = plan.all_slices(spec_text)
            if own and slices and all(done for done, _ in slices):
                kind, how = (("plan_all_ticked_in_now", "is in Now with every slice ticked") if section == "Now"
                             else ("plan_built_in_next", "is built (every slice ticked) but still in Next"))
                found.append(_problem(kind, str(master), True, project=row[0],
                                      detail=f"{row[0]} {how}; repair closes it in the plan "
                                             "(needs maintenance mode)."))
    log_rows = len(rows.get("Update log", []))
    lines = len(text.split("\n"))
    if lines > PLAN_MAX_LINES or log_rows > PLAN_MAX_LOG:
        name, size = plan.longest_section(text)
        add("plan_too_long", master,
            f"the plan is {lines} lines with {log_rows} Update log rows; the longest part is {name} ({size} lines). "
            "`plan tidy --show` lists what can move out, and `plan tidy` moves it.")
    index = space.archive_dir / "index.md"
    indexed = index.read_text(encoding="utf-8") if index.is_file() else ""
    if space.archive_dir.is_dir():
        for f in sorted(space.archive_dir.iterdir()):
            if re.match(rf"{space.prefix}-\d+.*\.md$", f.name) and f.name not in indexed:
                add("plan_archive_not_indexed", f, f"{f.name} is in the archive but not in its index; "
                    "repair adds it.", fixable=True)
    if own:
        found += _own_plan_problems(space, text, now)
    return found


def _table_widths(text: str, section: str) -> tuple[int, list[int]]:
    """(cell count of the header, cell count of each data row) for a section's table; ValueError
    when the section or its table is missing."""
    from afc import plan

    lines = text.split("\n")
    start, end = plan._section_span(lines, section)
    table = [ln for ln in lines[start:end] if ln.lstrip().startswith("|")]
    if len(table) < 2:
        raise ValueError(section)
    counts = [len(plan._split_row(ln)) for ln in table]
    return counts[0], counts[2:]


def _header_status(spec_text: str) -> str:
    m = re.search(r"^Size:.*?Status:\s*([^·\n]*?)\s*(?:·|$)", spec_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _own_plan_problems(space, text: str, now: list[list[str]]) -> list[dict]:
    """The checks that only make sense for Flight Control's own plan: a worktree's own copy that differs,
    and uncommitted edits (skipped while a spec in Now still has an open slice)."""
    from afc import cli_plan, plan

    found: list[dict] = []
    root = space.base.parent
    here = _cli().afc_root() / "docs" / "master-plan.md"
    if root.resolve() != _cli().afc_root().resolve() and here.is_file() and \
            here.read_text(encoding="utf-8") != text:
        clean = _git(_cli().afc_root(), "status", "--short", "--", "docs/master-plan.md") == ""
        found.append(_problem("plan_copy_differs", str(here), clean,
                              detail="This worktree's own copy of the master plan differs from the one on dev; "
                                     + ("repair replaces it with dev's." if clean else
                                        "it has uncommitted edits, so repair leaves it alone.")))
    building = False
    for row in now:
        spec = cli_plan._spec_path(space, row)
        if spec.is_file() and any(not done for done, _ in plan.all_slices(spec.read_text(encoding="utf-8"))):
            building = True
    if not building and _git(root, "status", "--short", "--", "docs/master-plan.md", "docs/specs"):
        found.append(_problem("plan_uncommitted", str(space.master), False,
                              detail="Flight Control's plan: the master plan or a spec has changes that are "
                                     "not committed yet."))
    return found


def _repair_plan(home: Path, found: list[dict]) -> list[str]:
    from argparse import Namespace

    from afc import cli_plan

    cli = _cli()
    out: list[str] = []
    if not found:
        return out
    for p in [p for p in found if p["kind"] == "plan_archive_not_indexed"]:
        out.append(_repair_archive_index(home, p))
    left = {p["kind"] for p in found if p["kind"] in PLAN_WHY_LEFT}
    if left:
        why = "; ".join(PLAN_WHY_LEFT[k] for k in PLAN_WHY_LEFT if k in left)
        out.append(f"Left the other plan problems as they are, because they need a decision: {why}.")
    found = [p for p in found if p["kind"] in PLAN_CLOSES]
    ordered = sorted(found, key=lambda p: p["kind"] != "plan_all_ticked_in_now")
    for p in ordered:
        if p["kind"] == "plan_copy_differs":
            src = cli_plan._plan_root() / "docs" / "master-plan.md"
            Path(p["path"]).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            out.append("Replaced this worktree's copy of the master plan with the one on dev.")
            continue
        if not maintain_enabled(home, current_session()):
            out.append(f"{p['project']} is out of date in the plan; closing it changes Flight Control's "
                       "own plan, so it needs maintenance mode (/afc mm).")
            continue
        try:
            if p["kind"] == "plan_built_in_next":
                cli_plan.cmd_start(Namespace(id=p["project"]))
            cli_plan.cmd_done(Namespace(id=p["project"]))
            out.append(f"Closed {p['project']} in the master plan.")
        except cli.CliError as exc:
            out.append(f"Could not close {p['project']} in the plan: {exc}")
    return out


def _repair_archive_index(home: Path, p: dict) -> str:
    """Add the row for an archived spec that the archive index lacks, read from the spec file itself."""
    from afc import cli_plan

    path = Path(p["path"])
    if not p.get("project") and not maintain_enabled(home, current_session()):
        return (f"{path.name} is missing from the archive index; adding it changes Flight Control's own "
                "plan, so it needs maintenance mode (/afc mm).")
    text = path.read_text(encoding="utf-8")
    sid = re.match(r"([A-Za-z]+-\d+)", path.name).group(1)
    title = re.search(r"^#\s*\S+\s*[—-]\s*(.+?)\s*$", text, re.MULTILINE)
    done = re.search(r"Done:\s*(\d{4}-\d{2}-\d{2})", text)
    row = [sid, title.group(1) if title else path.stem, done.group(1) if done else "-", path.name]
    index = path.parent / "index.md"
    old = index.read_text(encoding="utf-8") if index.is_file() else ""
    index.write_text(cli_plan._archive_index(old, row), encoding="utf-8")
    return f"Added {path.name} to the archive index."


def switch_addons(root: Path, found: list[dict]) -> tuple[int, int]:
    """Act on add-on problems: switch off the ones not allowed, back on the ones allowed again.
    Returns (switched off, switched back on). On any error the settings file is put back as it was
    and the error is raised."""
    found = [p for p in found if p["kind"] in ADDONS]
    if not found:
        return 0, 0
    check_settings(root)
    undo = Undo(settings_path(root))
    undo.save_settings()
    try:
        keep = [i for i in blocked_addons(root) if i not in
                {p["addon"] for p in found if p["kind"] == "addon_unblock"}]
        now = [p["addon"] for p in found if p["kind"] == "addon_not_allowed"]
        block_addons(root, [*keep, *now])
    except BaseException:
        undo.rollback()
        raise
    return len(now), len(found) - len(now)



def _upgrade_plan(plan_dir: Path) -> None:
    """Add a master plan, carry the old progress text over, archive progress.md."""
    from afc.config import afc_root

    old = plan_dir / "progress.md"
    text = old.read_text(encoding="utf-8")
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    template = afc_root() / "templates" / "workspace" / "plan" / "master-plan.md"
    master = template.read_text(encoding="utf-8").rstrip("\n")
    (plan_dir / "specs").mkdir(exist_ok=True)
    (plan_dir / "archive").mkdir(exist_ok=True)
    (plan_dir / "master-plan.md").write_text(
        master + "\n\n## Earlier progress\n\n" + "\n".join(lines).strip("\n") + "\n", encoding="utf-8")
    shutil.move(str(old), str(plan_dir / "archive" / "progress-legacy.md"))


def cmd_relocate(args: argparse.Namespace) -> dict:
    cli = _cli()
    home = afc_home()
    reg = load_registry(home)
    project = reg.get(args.name)
    if project is None:
        raise cli.CliError(cli._unknown_name(args.name))
    new = Path(args.path).expanduser().resolve()
    if not new.is_dir():
        raise cli.CliError(f"Folder {new} does not exist.")
    protected = [Path.home().resolve(), home.resolve(), cli.afc_root().resolve()]
    if new == Path(new.anchor) or any(p == new or p.is_relative_to(new) for p in protected):
        raise cli.CliError(f"{new} holds more than one project's code. Pick the app's own folder.")
    for other in reg.projects.values():
        if other.name != project.name and Path(other.code_path).resolve() == new:
            raise cli.CliError(f"{new} is already the code folder of {other.name}.")
    reg.update(project.name, code_path=str(new))
    if reg.active_name == project.name:
        undo = cli._settings_undo()
        try:
            cli._commit(home, reg, project, undo)
        except BaseException:
            undo.rollback()
            raise
    else:
        save_registry(home, reg)
    return {"relocated": project.name, "code_path": str(new)}


def find_problems(home: Path, with_addons: bool = True) -> list[dict]:
    """Every problem as {kind, project?, path, detail, fixable}. Reads only. with_addons=False leaves out
    the add-on part, which the welcome handles itself."""
    cli = _cli()
    reg = load_registry(home)
    problems: list[dict] = root_problems(cli.afc_root()) if not is_test_copy(cli.afc_root(), home) else []
    problems += behind_problems(cli.afc_root(), home)
    from afc import cli_plan, plan

    fc_space = plan.flight_control_space(cli_plan._plan_root())
    problems += plan_problems(fc_space)
    problems += _findings_problems(fc_space)
    for p in reg.projects.values():
        if Path(p.workspace_path).is_dir():
            proj_space = plan.project_space(Path(p.workspace_path))
            problems += plan_problems(proj_space, p.name)
            problems += _findings_problems(proj_space)
    if (home / "maintain").exists():
        problems.append(_problem("stale_maintain", str(home / "maintain"), True,
                                 detail="An old global maintenance switch is left over; it is ignored, "
                                        "and repair removes it."))
    owned: set[Path] = set()
    for p in reg.projects.values():
        owned.add(Path(p.workspace_path).resolve())
        if not Path(p.code_path).is_dir():
            problems.append(_problem(
                "code_missing", p.code_path, False, project=p.name,
                detail=f"{p.name}: its code folder is gone from {p.code_path}. If it moved, "
                       "relocate it; if it's no longer wanted, remove the project."))
        if not Path(p.workspace_path).is_dir():
            ours = Path(p.workspace_path).resolve() == (home / "projects" / p.name).resolve()
            problems.append(_problem(
                "workspace_missing", p.workspace_path, ours, project=p.name,
                detail=f"{p.name}: its Flight Control workspace is missing; "
                       + ("repair recreates an empty one." if ours else "it lives outside ~/.A-FC.")))
        elif (Path(p.workspace_path) / "plan" / "progress.md").is_file() and not (
                Path(p.workspace_path) / "plan" / "master-plan.md").exists():
            problems.append(_problem(
                "old_plan_format", str(Path(p.workspace_path) / "plan"), True, project=p.name,
                detail=f"{p.name}: still uses the old progress list; repair upgrades it to a master plan."))
        problems += _decisions_problems(p)
        problems += _architecture_problems(p)
    projects_dir = home / "projects"
    if projects_dir.is_dir():
        for d in sorted(projects_dir.iterdir()):
            if d.is_dir() and d.resolve() not in owned:
                problems.append(_problem(
                    "orphan_workspace", str(d), True,
                    detail=f"{d.name}: a leftover workspace that belongs to no project."))
    try:
        current, ours = granted_now(cli.afc_root())
    except GrantError as exc:
        problems.append(_problem("settings_unreadable", "", False, detail=str(exc)))
        return problems
    if with_addons:
        problems += addon_problems(cli.afc_root())
    problems += _tools_problems(cli.afc_root(), reg)
    problems += _tracked_deny_problems(cli.afc_root())
    wanted = _wanted(reg)
    foreign = foreign_roots_for(home, reg)
    for entry in current:
        if any(_inside(entry, r) for r in foreign):
            problems.append(_problem("foreign_access", entry, True,
                                     detail=f"This test copy still has access to {entry}, which belongs to the "
                                            "real Flight Control workspace; repair removes it."))
        elif not Path(entry).exists():
            problems.append(_problem("gone_access", entry, True,
                                     detail=f"Claude still has access to {entry}, which no longer exists."))
        elif entry in ours and entry not in wanted:
            problems.append(_problem("stale_access", entry, True,
                                     detail=f"Claude still has access to {entry}, which isn't the active project."))
    for entry in wanted:
        if entry not in current:
            problems.append(_problem("missing_access", entry, True,
                                     detail=f"The active project's folder {entry} isn't open to Claude."))
    return problems


LOG_SECTION = ("\n## Log\n\nDated entries, newest last. Each says what was decided and why. "
               "Add new entries here, at the end.\n")


def _decisions_problems(project) -> list[dict]:
    """An older decisions.md has no `## Log`, so new entries would land under Standing Corrections."""
    path = Path(project.workspace_path) / "plan" / "decisions.md"
    if not path.is_file() or "\n## Log" in "\n" + path.read_text(encoding="utf-8"):
        return []
    return [_problem("decisions_no_log", str(path), True, project=project.name,
                     detail=f"{project.name}: decisions.md has no Log section; repair adds one so "
                            "decisions stop landing under the always/never rules.")]


def architecture_is_bare(path: Path) -> bool:
    """True when the project's architecture.md is still the empty template (whitespace aside)."""
    template = _cli().afc_root() / "templates" / "workspace" / "plan" / "architecture.md"
    if not path.is_file() or not template.is_file():
        return False
    return " ".join(path.read_text(encoding="utf-8").split()) == " ".join(template.read_text(encoding="utf-8").split())


def _architecture_problems(project) -> list[dict]:
    """A project with a done slice whose architecture.md is still the bare template (whitespace
    aside). Claude fills it from the code, so it is reported, never auto-fixed."""
    path = Path(project.workspace_path) / "plan" / "architecture.md"
    if not project.last_slice or not architecture_is_bare(path):
        return []
    return [_problem("architecture_empty", str(path), False, project=project.name,
                     detail=f"{project.name}: slices are done but architecture.md is still the empty "
                            "template; Claude fills it in from the code.")]


def _findings_problems(space) -> list[dict]:
    """Check findings.md for rows with no State, or claiming fixed in a spec that is not done."""
    from afc import plan
    fpath = plan.findings_path(space)
    if not fpath.is_file():
        return []
    try:
        text = fpath.read_text(encoding="utf-8")
        rows = plan.read_rows(text, "All findings")
    except Exception:
        return []
    # Build a set of done spec IDs from the archive index and archive directory
    done_ids: set[str] = set()
    archive = space.archive_dir
    if archive.is_dir():
        for f in archive.iterdir():
            m = re.match(rf"({re.escape(space.prefix)}-\d+)", f.name)
            if m:
                done_ids.add(m.group(1))
    index = archive / "index.md"
    if index.is_file():
        for ln in index.read_text(encoding="utf-8").split("\n"):
            if ln.lstrip().startswith("|"):
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if cells and re.match(rf"{re.escape(space.prefix)}-\d+$", cells[0]):
                    done_ids.add(cells[0])

    found = []
    for row in rows:
        fid = row[0] if row else ""
        state = row[2].strip() if len(row) > 2 else ""
        if not state:
            found.append(_problem("finding_no_state", str(fpath), False,
                                  detail=f"Finding {fid} has no State; set it to open, fixed, "
                                         "waiting on you, parked, or no change needed."))
        elif state.startswith("fixed in "):
            spec_id = state[len("fixed in "):].strip().split()[0] if state[len("fixed in "):].strip() else ""
            if spec_id and spec_id not in done_ids:
                found.append(_problem("finding_fixed_not_done", str(fpath), False,
                                      detail=f"Finding {fid} says fixed in {spec_id}, but {spec_id} "
                                             "is not in the archive; update the State or finish the spec."))
    return found


def foreign_roots_for(home: Path, reg) -> list[Path]:
    """In a test home, the real ~/.A-FC and the code folders of projects registered only there."""
    from afc.hooks.common import Context
    from afc.hooks.rules_paths import foreign_roots

    return foreign_roots(Context(home=home, root=_cli().afc_root(), active=None, maintain=False,
                                 projects=tuple(reg.projects.values())))


def _inside(entry: str, root: Path) -> bool:
    try:
        path = Path(entry).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    return path == root or path.is_relative_to(root)


def _wanted(reg) -> list[str]:
    """The active project's folders that exist: what folder access should be."""
    active = reg.active()
    if active is None:
        return []
    dirs = [Path(active.code_path), Path(active.workspace_path)]
    return [str(d.resolve()) for d in dirs if d.is_dir()]


def _tracked_deny_problems(root: Path) -> list[dict]:
    """The tracked .claude/settings.json list and the data file's list must agree (FC-038)."""
    from afc import connectors

    want, have = connectors.tracked_names(root), connectors.tracked_in_settings(root)
    try:  # names the user asked for in plain words are taken out of the tracked file (slice 3)
        from afc.config import afc_home
        asked = {connectors.PREFIX + n for n in connectors.names(connectors.load(afc_home()))}
    except Exception:
        asked = set()
    still = sorted(set(have) & asked)
    if still:  # an update or edit put a wanted name back in the tracked list
        return [_problem("tracked_deny_wanted", str(root / ".claude" / "settings.json"), False,
                         detail="The connectors held back from the first start still list "
                                + ", ".join(still) + ", which you asked for. Ask for it again "
                                "(sh bin/afc connectors add) to turn it back on.")]
    if set(want) - asked == set(have) - asked:
        return []
    diff = sorted((set(want) ^ set(have)) - asked)
    return [_problem("tracked_deny_differs", str(root / ".claude" / "settings.json"), False,
                     detail="The connectors held back from the first start differ between "
                            "afc-connectors.json and .claude/settings.json: " + ", ".join(diff) + ".")]


def _problem(kind: str, path: str, fixable: bool, detail: str, project: str = "") -> dict:
    found = {"kind": kind, "path": path, "detail": detail, "fixable": fixable}
    if project:
        found["project"] = project
    return found


def root_problems(root: Path, git: Callable[..., str | None] | None = None) -> list[dict]:
    """Git problems in Flight Control's own folder: a detached HEAD, uncommitted changes, a branch
    that is neither main nor dev, and no origin remote. Reads only. When git can't run or can't
    answer there are no git problems: nothing is guessed. `git` is the runner; None means _git."""
    run = git if git is not None else _git
    status = run(root, "status", "--porcelain=v2", "--branch")
    if status is None:
        return []
    found: list[dict] = []
    head = _head_branch(status)
    dirty = any(not line.startswith("#") for line in status.splitlines())
    if head == "(detached)":
        on_main = run(root, "merge-base", "--is-ancestor", "HEAD", "main") is not None
        if dirty:
            how, fixable = "It has uncommitted changes, so repair leaves it alone.", False
        elif not on_main:
            how, fixable = ("Its commit is not on main, so repair leaves it alone rather than risk "
                            "losing it.", False)
        else:
            how, fixable = "Its commit is already on main, so repair puts it back on main.", True
        found.append(_problem(
            "root_detached", str(root), fixable,
            detail="Flight Control's own copy is on a detached HEAD, not on a branch, so it can't "
                   "update itself. " + how))
    elif head is not None and head not in ROOT_BRANCHES:
        found.append(_problem(
            "root_branch", str(root), False,
            detail=f"Flight Control's own copy is on the branch {head}, which is neither main nor dev. "
                   "Switch it back onto main or dev."))
    if dirty:
        found.append(_problem(
            "root_dirty", str(root), False,
            detail="Flight Control's own copy has uncommitted changes, so it can't be updated safely. "
                   "Look at them yourself; Flight Control leaves them alone."))
    remotes = run(root, "remote")
    if remotes is not None and "origin" not in remotes.split():
        found.append(_problem(
            "root_no_origin", str(root), False,
            detail="Flight Control's own copy has no origin remote, so it has nowhere to fetch "
                   "updates from."))
    return found


def is_test_copy(root: Path, home: Path) -> bool:
    """A test copy is a linked git worktree of A-FC whose workspace is not the real ~/.A-FC."""
    try:
        if home == (Path.home() / ".A-FC").resolve():
            return False
    except (OSError, RuntimeError):
        return False
    git_dir = _git(root, "rev-parse", "--absolute-git-dir")
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return bool(git_dir and common and Path(git_dir.strip()).resolve() != Path(common.strip()).resolve())


def behind_problems(root: Path, home: Path) -> list[dict]:
    """A test copy whose commit is an older commit of dev. Reads only. Fixable when the copy is a
    detached HEAD with no uncommitted changes: repair then moves it to the tip of dev."""
    if not is_test_copy(root, home):
        return []
    head = _git(root, "rev-parse", "HEAD")
    tip = _git(root, "rev-parse", "--verify", "-q", "dev")
    if not head or not tip or head.strip() == tip.strip():
        return []
    if _git(root, "merge-base", "--is-ancestor", "HEAD", "dev") is None:
        return []  # not simply behind dev: nothing is guessed
    count = (_git(root, "rev-list", "--count", "HEAD..dev") or "?").strip()
    status = _git(root, "status", "--porcelain=v2", "--branch")
    detached = status is not None and _head_branch(status) == "(detached)"
    clean = status is not None and not any(not l.startswith("#") for l in status.splitlines())
    fixable = detached and clean
    return [_problem(
        "test_copy_behind", str(root), fixable,
        detail=f"This test copy is {count} commits behind dev, so testing it says nothing about today's "
               + ("build. Repair moves it to the tip of dev." if fixable else
                  "build. It has its own changes or a branch, so repair leaves it alone."))]


def root_git_note() -> str | None:
    """One sentence when git can't be run at all, else None. The check then reports no git
    problems for Flight Control's own folder rather than guessing."""
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return "Git couldn't run, so Flight Control's own folder wasn't checked."
    return None


def _head_branch(status: str) -> str | None:
    """The branch named by `git status --branch`, or "(detached)" when HEAD is detached."""
    for line in status.splitlines():
        if line.startswith("# branch.head "):
            return line.removeprefix("# branch.head ")
    return None


def _git(root: Path, *args: str) -> str | None:
    """git's output in the folder, or None when git can't run or answers with an error. Never raises."""
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def addon_problems(root: Path) -> list[dict]:
    """The add-on part of the health check. Reads only."""
    try:
        ok = addons.allowed(root)
    except ValueError as exc:
        return [_problem("addon_list_unreadable", "", False, detail=str(exc))]
    found: list[dict] = []
    off, note = addons.blocked(root)
    if note is not None:
        return found  # state unknown: don't guess
    for name in off:
        p = _problem("addon_not_allowed", name, True,
                     detail=f"{name} isn't on the allowed list, so Flight Control switches it off in "
                            "its own sessions from the next start. It still works everywhere else.")
        p["addon"] = name
        found.append(p)
    for name in blocked_addons(root):
        if name in ok:
            p = _problem("addon_unblock", name, True,
                         detail=f"{name} is on the allowed list again; repair switches it back on.")
            p["addon"] = name
            found.append(p)
    return found


def _tools_problems(root: Path, reg) -> list[dict]:
    active = reg.active()
    ws = Path(active.workspace_path) if active is not None and Path(active.workspace_path).is_dir() else None
    try:
        lines = tools.mismatches(root, ws)
    except (tools.ToolsError, GrantError) as exc:
        return [_problem("tools_unreadable", "", False, detail=str(exc))]
    if not lines:
        return []
    return [_problem("tools_out_of_sync", str(root), True,
                     detail=" ".join(lines) + " Repair puts the active project's tools back.")]
