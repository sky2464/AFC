"""Shared guard pieces: hook input, runtime context, path helpers, Bash parsing.

Hooks read one PreToolUse event as JSON on stdin. Anything unreadable
raises GuardInputError so the caller can fail closed.
"""

import json
import os
import re
import shlex
import tempfile
from dataclasses import dataclass
from pathlib import Path

from afc.config import afc_home, afc_root, maintain_enabled
from afc.registry import Project, RegistryError, load_registry

WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
POLICY_REASON = "Flight Control's own settings can't be changed this way"

_REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
_FD_DUP = ">&"
_SEPARATORS = {";", "&&", "||", "|", "&", "(", ")"}
_FILE_COMMANDS = {"cp", "mv", "rsync"}
_WRAPPERS = {"sudo", "env", "nohup", "command", "exec", "time"}
_SHELLS = {"bash", "sh", "zsh"}
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_FD_WORD = re.compile(r"^(\d+|-)$")
_SETTINGS_NAMES = ("settings.json", "settings.local.json")


class GuardInputError(Exception):
    """The hook input could not be read as a PreToolUse event."""


@dataclass
class Context:
    home: Path
    root: Path
    active: Project | None
    maintain: bool


def resolve_path(raw: str, cwd: str | None = None) -> Path:
    """Expand ~, resolve a relative path against cwd (default /), and resolve symlinks."""
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(cwd or "/") / path
    return path.resolve()


def read_event(text: str) -> dict:
    """Parse the hook's stdin text into a dict. Empty, non-JSON or non-object input is an error."""
    if not text or not text.strip():
        raise GuardInputError("hook input is empty")
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise GuardInputError(f"hook input is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GuardInputError("hook input is not a JSON object")
    return data


def load_context() -> Context:
    """Build the guard context from the workspace. A corrupt registry means no active project."""
    home = afc_home()
    try:
        active = load_registry(home).active()
    except RegistryError:
        active = None
    return Context(
        home=home,
        root=afc_root(),
        active=active,
        maintain=maintain_enabled(home),
    )


def target_path(event: dict) -> Path | None:
    """Resolved file path a write tool is about to touch, or None when it has none."""
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(raw, str) or not raw:
        return None
    return resolve_path(raw, event.get("cwd"))


def string_values(obj) -> list[str]:
    """Every string nested anywhere inside obj."""
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for value in obj.values() for s in string_values(value)]
    if isinstance(obj, list):
        return [s for value in obj for s in string_values(value)]
    return []


def allowed_roots(ctx: Context) -> list[Path]:
    """Directories a write may land in. Everything is resolved."""
    roots: list[Path] = []
    if ctx.active is not None:
        roots.append(Path(ctx.active.code_path))
        roots.append(Path(ctx.active.workspace_path))
    roots.append(ctx.home)
    roots.append(Path.home() / ".claude")
    roots.append(Path(tempfile.gettempdir()))
    roots.append(Path("/tmp"))
    roots.append(Path("/private/tmp"))
    if ctx.maintain:
        roots.append(ctx.root)
    return [resolve_path(str(p)) for p in roots]


def policy_reason(path: Path, ctx: Context) -> str | None:
    """Flight Control's own control files, which no write may change through the guard."""
    protected = (ctx.home / "maintain", ctx.home / "projects.json", ctx.home / "projects.md")
    if any(path == resolve_path(str(p)) for p in protected):
        return POLICY_REASON
    claude = resolve_path(str(Path.home() / ".claude"))
    if path.name in _SETTINGS_NAMES and _within(path, claude):
        return POLICY_REASON
    if not ctx.maintain and _within(path, resolve_path(str(ctx.root / ".claude"))):
        return POLICY_REASON
    return None


def check_paths_reason(path: Path, ctx: Context) -> str | None:
    """Why a single resolved path may not be written, or None when it may."""
    reason = policy_reason(path, ctx)
    if reason:
        return reason
    if _within(path, ctx.root) and not ctx.maintain:
        return f"{path} is inside the A-FC repo and needs maintenance mode"
    if any(_within(path, root) for root in allowed_roots(ctx)):
        return None
    if ctx.active is None:
        return f"no active project: pick a project — type /afc before writing {path}"
    return f"{path} is outside the active project, so the write is blocked"


def bash_write_targets(command: str, cwd: str = "/") -> list[str]:
    """Best-effort absolute paths a shell command writes to. Unparseable input gives [].

    Covers redirects (>, >>, >|, &>, >&word), tee, cp/mv/rsync (last argument or -t DIR),
    leading assignments and wrappers, `bash|sh|zsh -c`, and `cd` earlier in the chain.
    Targets with an unexpanded `$` or a backtick are skipped.
    """
    try:
        lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return []
    base = resolve_path(cwd)
    targets: list[str] = []
    for words, redirects in _commands(tokens):
        for raw in redirects:
            _add_target(targets, raw, base)
        words = _strip_prefix(words)
        if not words:
            continue
        name = Path(words[0]).name
        args = words[1:]
        if name == "cd":
            base = _cd_base(args, base)
        elif name in _SHELLS and "-c" in args:
            index = args.index("-c")
            if index + 1 < len(args):
                targets.extend(bash_write_targets(args[index + 1], str(base)))
        else:
            for raw in _command_targets(name, args):
                _add_target(targets, raw, base)
    return targets


def _within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def _commands(tokens: list[str]):
    """Yield (words, redirect_targets) for each simple command in a token stream."""
    words: list[str] = []
    redirects: list[str] = []
    ops = _REDIRECTS | {_FD_DUP}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if tok in _SEPARATORS:
            if words or redirects:
                yield words, redirects
            words, redirects = [], []
        elif tok in _REDIRECTS:
            if nxt is not None:
                redirects.append(nxt)
            i += 1
        elif tok == _FD_DUP:
            if nxt is not None and not _FD_WORD.match(nxt):
                redirects.append(nxt)
            i += 1
        elif tok.isdigit() and nxt in ops:
            pass  # file-descriptor prefix such as the 2 in 2>&1
        else:
            words.append(tok)
        i += 1
    if words or redirects:
        yield words, redirects


def _strip_prefix(words: list[str]) -> list[str]:
    """Drop leading VAR=value assignments, wrapper commands and options."""
    i = 0
    while i < len(words) and (
        _ASSIGNMENT.match(words[i]) or words[i] in _WRAPPERS or words[i].startswith("-")
    ):
        i += 1
    return words[i:]


def _command_targets(name: str, args: list[str]) -> list[str]:
    positional = [a for a in args if not a.startswith("-")]
    if name == "tee":
        return positional
    if name in _FILE_COMMANDS:
        destination = _target_dir_option(args)
        if destination is not None:
            return [destination]
        return positional[-1:] if len(positional) >= 2 else []
    return []


def _target_dir_option(args: list[str]) -> str | None:
    """Destination named by cp/mv/rsync -t DIR, -tDIR, --target-directory[=]DIR."""
    for i, arg in enumerate(args):
        if arg in ("-t", "--target-directory") and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--target-directory="):
            return arg.split("=", 1)[1]
        if arg.startswith("-t") and not arg.startswith("--") and len(arg) > 2:
            return arg[2:]
    return None


def _cd_base(args: list[str], base: Path) -> Path:
    positional = [a for a in args if not a.startswith("-")]
    if not positional:
        return Path.home()
    expanded = _expand(positional[0])
    if expanded is None:
        return base  # cannot know the directory; keep the current base (best effort)
    return resolve_path(expanded, str(base))


def _add_target(targets: list[str], raw: str, base: Path) -> None:
    expanded = _expand(raw)
    if not expanded or expanded == "/dev/null":
        return
    targets.append(str(resolve_path(expanded, str(base))))


def _expand(raw: str) -> str | None:
    """Expand ~ and environment variables; None when something is still unexpanded."""
    expanded = os.path.expandvars(os.path.expanduser(raw))
    if "$" in expanded or "`" in expanded:
        return None
    return expanded
