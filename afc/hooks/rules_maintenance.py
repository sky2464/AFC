"""Maintenance rules: while Flight Control itself is being worked on, no project is touched,
and Flight Control's own folder only changes while maintenance mode is on.

In maintenance mode, writes into any registered project's code or workspace folder, and git
commands that run in or point at those folders, are blocked. Reading stays allowed. Outside
maintenance mode `check_maintenance` does nothing; `check_own_copy` blocks git that changes the
A-FC folder itself (reading git is always fine). In that folder, whatever the mode, merges must
fast-forward and checkout/switch must land on a local branch (never a detached HEAD).
"""

import subprocess
from pathlib import Path

from afc.hooks.common import (
    WRITE_TOOLS,
    Context,
    bash_write_targets_or_none,
    resolve_path,
    target_path,
)
from afc.hooks.rules_git import parse_git, simple_commands

MERGE_REASON = ("this merge in the A-FC folder wouldn't fast-forward "
                "— run it yourself if you mean it")
MERGE_UNKNOWN_REASON = ("Flight Control couldn't confirm this merge in the A-FC folder fast-forwards "
                        "— run it yourself if you mean it")
DETACH_REASON = ("this would leave the A-FC folder on a detached HEAD "
                 "— switch to the branch main (or dev) instead")
_MERGE_VALUE_OPTS = {"-m", "-F", "-s", "-X", "--into-name", "--message", "--file", "--strategy",
                     "--strategy-option"}
_NEW_BRANCH_OPTS = {"-b", "-B", "-c", "-C", "--orphan", "--create", "--force-create"}
_GIT_TIMEOUT = 5

_LOCATION_OPTS = {"-C", "--git-dir", "--work-tree"}
_VALUE_OPTS = {*_LOCATION_OPTS, "-c", "--namespace", "--config-env"}

# Git that only reads. Anything not listed here or in _CONDITIONAL counts as changing, so a new
# git verb is guarded by default.
_READ_ONLY = {
    "", "status", "log", "diff", "show", "describe", "rev-parse", "rev-list", "ls-remote",
    "ls-files", "ls-tree", "blame", "shortlog", "cat-file", "grep", "merge-base", "name-rev",
    "whatchanged", "show-ref", "for-each-ref", "diff-tree", "diff-files", "diff-index",
    "count-objects", "check-ignore", "verify-commit", "verify-tag", "var", "help", "version",
}
# Display-only flags of `tag` and `branch`; a positional is a listing pattern only with one of
# the listing flags (otherwise it names something to create).
_LISTING = {"-l", "--list", "--contains", "--no-contains", "--merged", "--no-merged",
            "--points-at", "--show-current"}
_DISPLAY = {"-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose", "-i", "--ignore-case",
            "--no-color", "--color", "--column", "--no-column", "--abbrev"}
_CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "-l", "--list",
                 "--show-origin", "--show-scope"}


def _project_folders(ctx: Context) -> list[tuple[str, Path]]:
    """(project name, folder) for every project's code and workspace folder.

    A folder that is, or holds, Flight Control or its workspace home is skipped: blocking it
    would block maintenance itself (the registry should never hold one; remove and relocate
    refuse them).
    """
    keep = [ctx.root.resolve(), ctx.home.resolve()]
    folders: list[tuple[str, Path]] = []
    for project in ctx.projects:
        for raw in (project.code_path, project.workspace_path):
            folder = resolve_path(raw)
            if not any(k == folder or k.is_relative_to(folder) for k in keep):
                folders.append((project.name, folder))
    return folders


def _owner(path: Path, folders: list[tuple[str, Path]]) -> str | None:
    for name, folder in folders:
        if path == folder or path.is_relative_to(folder):
            return name
    return None


def _git_locations(words: list[str], base: Path) -> list[Path]:
    """Folders a git command works in: where it runs, plus -C, --git-dir and --work-tree.

    Git applies -C first, so later options are relative to the folder -C moved to.
    """
    found = [base]
    here = base
    i = 1
    while i < len(words) and words[i].startswith("-"):
        key, eq, inline = words[i].partition("=")
        takes_value = not eq and key in _VALUE_OPTS
        value = inline if eq else (words[i + 1] if takes_value and i + 1 < len(words) else "")
        if value and key in _LOCATION_OPTS:
            place = resolve_path(value, str(here))
            if key == "-C":
                here = place
            found.append(place)
        i += 2 if takes_value else 1
    return found


def check_maintenance(event: dict, ctx: Context) -> str | None:
    """Return a block reason when maintenance mode would reach into a project, else None."""
    if not ctx.maintain:
        return None
    folders = _project_folders(ctx)
    if not folders:
        return None
    tool = event.get("tool_name")
    if tool in WRITE_TOOLS:
        target = target_path(event)
        owner = _owner(target, folders) if target is not None else None
        return _write_reason(target, owner) if owner else None
    if tool != "Bash":
        return None
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return None
    cwd = event.get("cwd") or "/"
    for raw in bash_write_targets_or_none(command, cwd) or []:
        owner = _owner(Path(raw), folders)
        if owner:
            return _write_reason(Path(raw), owner)
    for words, base in simple_commands(command, cwd) or []:
        if parse_git(words) is None:
            continue
        for where in _git_locations(words, base):
            owner = _owner(where, folders)
            if owner:
                return (f"maintenance mode is on, so git can't run in {where} (project {owner}) "
                        "— project work needs maintenance mode off")
    return None


def _write_reason(path: Path, owner: str) -> str:
    return (f"maintenance mode is on, so {path} (project {owner}) is off limits "
            "— project work needs maintenance mode off")


def _listing_only(args: list[str]) -> bool:
    """True for `tag` / `branch` args that only list: display flags, and positionals only as
    patterns of a listing flag."""
    names = [a.split("=", 1)[0] for a in args if a.startswith("-")]
    if any(n not in _LISTING | _DISPLAY and not n.startswith(("-n", "--sort", "--format"))
           for n in names):
        return False
    positional = [a for a in args if not a.startswith("-")]
    return not positional or any(n in _LISTING for n in names)


def changes_git(sub: str, args: list[str]) -> bool:
    """True when a git subcommand may change the repository (unknown ones do)."""
    if sub in _READ_ONLY:
        return False
    if sub in ("tag", "branch"):
        return not _listing_only(args)
    if sub == "stash":
        return not args or args[0] not in ("list", "show")
    if sub == "remote":
        return bool(args) and not (set(args) <= {"-v", "--verbose"} or args[0] in ("show", "get-url"))
    if sub == "config":
        return not any(a.split("=", 1)[0] in _CONFIG_READS for a in args)
    if sub == "worktree":
        return not args or args[0] != "list"
    if sub == "reflog":
        return bool(args) and args[0] != "show"
    if sub == "fetch":  # only refs/remotes move, unless a refspec or tag flag reaches further
        return any(":" in a or a in ("--tags", "-t", "--update-head-ok", "-u") for a in args)
    return True


def _ask_git(location: list[str], base: Path, *args: str) -> int | None:
    """Exit code of a short git query in base; None when git can't answer."""
    if not base.is_dir():
        return None
    try:
        return subprocess.run(["git", *location, *args], cwd=base, capture_output=True,
                              timeout=_GIT_TIMEOUT).returncode
    except (OSError, subprocess.SubprocessError):
        return None


def _merge_reason(location: list[str], base: Path, args: list[str]) -> str | None:
    """Block reason for a merge that could make a merge commit; None when it fast-forwards."""
    longs = {a.split("=", 1)[0] for a in args if a.startswith("--")}
    if longs & {"--abort", "--continue", "--quit", "--ff-only"} and not longs & {"--no-ff", "--squash"}:
        return None
    if longs & {"--no-ff", "--squash"}:
        return MERGE_REASON
    targets, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif arg in _MERGE_VALUE_OPTS:
            skip = True
        elif not arg.startswith("-"):
            targets.append(arg)
    if len(targets) != 1:
        return MERGE_REASON
    code = _ask_git(location, base, "merge-base", "--is-ancestor", "HEAD", targets[0])
    if code == 0:
        return None
    return MERGE_REASON if code == 1 else MERGE_UNKNOWN_REASON


def _switch_reason(sub: str, location: list[str], base: Path, args: list[str]) -> str | None:
    """Block reason for a checkout/switch that would not land on a local branch."""
    if "--detach" in args or (sub == "switch" and "-d" in args):
        return DETACH_REASON
    if "--" in args:
        return None  # restoring files, HEAD stays where it is
    if any(a.split("=", 1)[0] in _NEW_BRANCH_OPTS or a.startswith(("-b", "-B")) and not a.startswith("--")
           for a in args):
        return None  # a new branch, not a detached HEAD
    positional = [a for a in args if not a.startswith("-") or a == "-"]
    if not positional:
        return None
    target = positional[0]
    code = _ask_git(location, base, "rev-parse", "--verify", "--quiet", f"refs/heads/{target}")
    if code == 0:
        return None
    if sub == "checkout" and code == 1:
        # not a branch: a tag, commit or remote branch would detach, a file path would not
        code = _ask_git(location, base, "rev-parse", "--verify", "--quiet", f"{target}^{{commit}}")
        if code == 1:
            return None
    return DETACH_REASON


def check_own_copy(event: dict, ctx: Context) -> str | None:
    """Return a block reason when git would damage the A-FC folder, else None.

    Changing git needs maintenance mode; merges that aren't fast-forwards and checkouts that
    leave a detached HEAD are blocked in either mode.
    """
    if event.get("tool_name") != "Bash":
        return None
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return None
    root = ctx.root.resolve()
    for words, base in simple_commands(command, event.get("cwd") or "/") or []:
        git = parse_git(words)
        if git is None:
            continue
        location, sub, args = git
        places = _git_locations(words, base)
        here = next((w for w in places[1:] or places if w == root or w.is_relative_to(root)), None)
        if here is None:
            continue
        if not ctx.maintain and changes_git(sub, args):
            return f"{here} is inside the A-FC repo and needs maintenance mode"
        if sub == "merge":
            reason = _merge_reason(location, base, args)
        elif sub in ("checkout", "switch"):
            reason = _switch_reason(sub, location, base, args)
        else:
            continue
        if reason:
            return reason
    return None
