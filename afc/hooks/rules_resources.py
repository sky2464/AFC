"""Company-resource rule: text or files from a workspace's resources/ must not reach a repo.

Writes inside the Flight Control workspace are always allowed; summaries belong there.
"""

from pathlib import Path

from afc.fingerprint import leaks, load_fingerprints
from afc.hooks.common import (
    CANT_FOLLOW,
    UNREADABLE_REASON,
    WRITE_TOOLS,
    Context,
    bash_write_targets_or_none,
    cd_base,
    expand_vars,
    lex,
    resolve_path,
    shell_script,
    split_commands,
    strip_prefix,
    target_path,
    track_assignments,
)

TEXT_REASON = ("this contains company resource text — keep it in the project workspace "
               "and write your own summary in the repo instead")
FILE_REASON = "this copies a company resource file out of the workspace — keep it in the workspace"
# Commands that carry whole trees, so naming projects/ or a parent of it counts as resources.
_TREE_COPY = {"cp", "mv", "rsync", "scp", "tar", "zip", "7z", "ditto"}
# Commands that send files off the machine; naming a resource is enough.
_REMOTE = {"scp", "sftp", "rsync", "curl", "wget"}
# Commands whose last positional argument is where the copy lands.
_COPY_LIKE = {"cp", "mv", "ln", "install", "ditto", "rsync", "scp"}


def _within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def active_fingerprints(ctx: Context) -> set[str]:
    """Fingerprints of the active project's resources; empty without one."""
    if ctx.active is None:
        return set()
    return load_fingerprints(Path(ctx.active.workspace_path))


def _is_resource(path: Path, home: Path, tree: bool) -> bool:
    """Under <home>/projects/<name>/resources; with tree, also projects/ or a parent of it."""
    projects = home / "projects"
    if _within(projects, path):
        return tree
    if not _within(path, projects):
        return False
    parts = path.relative_to(projects).parts
    return (len(parts) < 2 and tree) or (len(parts) >= 2 and parts[1] == "resources")


def _values(word: str) -> list[str]:
    """The word, plus the value of key=value / --opt=value forms (dd if=FILE)."""
    return [word, word.split("=", 1)[1]] if "=" in word else [word]


def _new_strings(tool_input) -> list[str]:
    """Only the new content a write tool would put in the file."""
    if not isinstance(tool_input, dict):
        return []
    out = [tool_input.get(k) for k in ("content", "new_string", "new_source")]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        out += [e.get("new_string") for e in edits if isinstance(e, dict)]
    return [s for s in out if isinstance(s, str)]


def _bash_reason(command: str, cwd: str, home: Path, outside: bool, depth: int = 0) -> str | None:
    """FILE_REASON when a command names a resource while something is written outside home."""
    tokens = lex(command)
    if tokens is None:
        return UNREADABLE_REASON
    base = resolve_path(cwd)
    env: dict = {}
    for words, _ in split_commands(tokens):
        words = strip_prefix(track_assignments(words, env))
        if not words:
            continue
        name = Path(words[0]).name
        if name == "cd":
            base = cd_base(words[1:], base)
            continue
        if (script := shell_script(words, base, depth)) is not None:
            if script is CANT_FOLLOW:
                return UNREADABLE_REASON
            reason = _bash_reason(script, str(base), home, outside, depth + 1)
            if reason:
                return reason
            continue
        tree = name in _TREE_COPY
        for word in words[1:]:
            for raw in _values(word):
                value = expand_vars(raw)
                if value is None:
                    if "resources" in raw or "projects" in raw:
                        return UNREADABLE_REASON
                    continue
                if value and _is_resource(resolve_path(value, str(base)), home, tree):
                    if outside or name in _REMOTE or _dest_outside(name, words[1:], base, home):
                        return FILE_REASON
    return None


def _dest_outside(name: str, args: list[str], base: Path, home: Path) -> bool:
    """A destination outside home: last positional of a copy-like command (_COPY_LIKE),
    dd of=, or any positional of an archiver (tar, zip, 7z), whose archive comes first."""
    positional = [a for a in args if not a.startswith("-") and "=" not in a]
    if name in ("tar", "zip", "7z"):
        dests = positional + [a.split("=", 1)[1] for a in args if a.startswith("--file=")]
    elif name in _COPY_LIKE:
        dests = positional[-1:] if len(positional) >= 2 else []
    else:
        dests = []
    dests += [a.split("=", 1)[1] for a in args if a.startswith("of=")]
    for raw in dests:
        value = expand_vars(raw)
        if value and ":" not in value and not _within(resolve_path(value, str(base)), home):
            return True
        if value and ":" in value and not value.startswith("/"):
            return True  # host:path — leaves the machine
    return False


def check_resources(event: dict, ctx: Context) -> str | None:
    """Reason to block a write or copy that would carry company resources out, or None."""
    tool = event.get("tool_name")
    home = resolve_path(str(ctx.home))
    if tool in WRITE_TOOLS:
        path = target_path(event)
        if path is None or _within(path, home):
            return None
        strings = _new_strings(event.get("tool_input"))
        if not strings:
            return None
        fps = active_fingerprints(ctx)
        return TEXT_REASON if any(leaks(s, fps) for s in strings) else None
    if tool != "Bash":
        return None
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command:
        return None
    cwd = event.get("cwd") or "/"
    targets = bash_write_targets_or_none(command, cwd)
    if targets is None:
        return UNREADABLE_REASON
    outside = any(not _within(Path(t), home) for t in targets)
    reason = _bash_reason(command, cwd, home, outside)
    if reason:
        return reason
    if outside:
        fps = active_fingerprints(ctx)
        words = lex(command) or []
        if leaks(command, fps) or any(leaks(w, fps) for w in words):
            return TEXT_REASON
    return None
