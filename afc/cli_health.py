"""Health commands: check, repair and relocate.

Registered into the main parser by afc.cli through register(). check only reads; repair fixes
what needs no decision (folder access, missing or leftover workspaces); relocate points a project
at its code folder after the user moved it. Nothing is ever deleted.
"""

import argparse
import shutil
from pathlib import Path

from afc import addons, tools
from afc.config import afc_home
from afc.registry import load_registry, save_registry
from afc.session_dirs import GrantError, block_addons, blocked_addons, drop_dirs, grant_dirs, granted_now
from afc.workspace import create_workspace

NAMES = ("check", "repair", "relocate")
ACCESS = ("stale_access", "gone_access", "missing_access")
ADDONS = ("addon_not_allowed", "addon_unblock")


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
    return {"ok": not problems, "problems": problems}


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
        elif p["kind"] == "old_plan_format":
            _upgrade_plan(Path(p["path"]))
            repaired.append(f"Upgraded {p['project']} to a master plan.")
        elif p["kind"] == "decisions_no_log":
            path = Path(p["path"])
            path.write_text(path.read_text(encoding="utf-8").rstrip("\n") + "\n" + LOG_SECTION, encoding="utf-8")
            repaired.append(f"Added a Log section to {p['project']}'s decisions.")
    access = [p for p in find_problems(home) if p["kind"] in ACCESS]
    if access:
        undo = cli._settings_undo()
        undo.save_settings()
        try:
            grant_dirs(cli.afc_root(), _wanted(reg))
            drop_dirs(cli.afc_root(), [p["path"] for p in access if p["kind"] == "gone_access"])
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
    found = [p for p in find_problems(home) if p["kind"] in ADDONS]
    if found:
        undo = cli._settings_undo()
        undo.save_settings()
        try:
            keep = [i for i in blocked_addons(cli.afc_root()) if i not in
                    {p["addon"] for p in found if p["kind"] == "addon_unblock"}]
            now = [p["addon"] for p in found if p["kind"] == "addon_not_allowed"]
            block_addons(cli.afc_root(), [*keep, *now])
        except BaseException:
            undo.rollback()
            raise
        if now:
            n = len(now)
            repaired.append(f"Switched off {n} add-on{'s' if n > 1 else ''} in Flight Control sessions; "
                            "this applies from the next start.")
        if len(found) > len(now):
            repaired.append("Switched back on add-ons that are now allowed; this applies from the next start.")
    return {"repaired": repaired, "left": find_problems(home)}


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


def find_problems(home: Path) -> list[dict]:
    """Every problem as {kind, project?, path, detail, fixable}. Reads only."""
    cli = _cli()
    reg = load_registry(home)
    problems: list[dict] = []
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
    problems += _addon_problems(cli.afc_root())
    problems += _tools_problems(cli.afc_root(), reg)
    wanted = _wanted(reg)
    for entry in current:
        if not Path(entry).exists():
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


def _wanted(reg) -> list[str]:
    """The active project's folders that exist: what folder access should be."""
    active = reg.active()
    if active is None:
        return []
    dirs = [Path(active.code_path), Path(active.workspace_path)]
    return [str(d.resolve()) for d in dirs if d.is_dir()]


def _problem(kind: str, path: str, fixable: bool, detail: str, project: str = "") -> dict:
    found = {"kind": kind, "path": path, "detail": detail, "fixable": fixable}
    if project:
        found["project"] = project
    return found


def _addon_problems(root: Path) -> list[dict]:
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
                     detail=f"Flight Control switched off {name} in its own sessions because it isn't "
                            "on the allowed list. It still works everywhere else.")
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
