"""Shared guard pieces: hook input, runtime context, and path helpers.

Hooks read one PreToolUse event as JSON on stdin. Anything unreadable
raises GuardInputError so the caller can fail closed.
"""

import json
import shlex
import tempfile
from dataclasses import dataclass
from pathlib import Path

from afc.config import afc_home, afc_root, maintain_enabled
from afc.registry import Project, RegistryError, load_registry

WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")

_REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
_SEPARATORS = {";", "&&", "||", "|", "&", "(", ")"}
_FILE_COMMANDS = {"cp", "mv", "rsync"}


class GuardInputError(Exception):
    """The hook input could not be read as a PreToolUse event."""


@dataclass
class Context:
    home: Path
    root: Path
    active: Project | None
    maintain: bool


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
    return _resolve(raw, event.get("cwd"))


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
    return [_resolve(str(p)) for p in roots]


def bash_write_targets(command: str) -> list[str]:
    """Best-effort list of paths a shell command writes to. Unparseable input gives []."""
    try:
        lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    targets: list[str] = []
    for words, redirects in _commands(tokens):
        targets.extend(redirects)
        if not words:
            continue
        name = Path(words[0]).name
        args = [w for w in words[1:] if not w.startswith("-")]
        if name == "tee":
            targets.extend(args)
        elif name in _FILE_COMMANDS and len(args) >= 2:
            targets.append(args[-1])
    return [t for t in targets if t and t != "/dev/null"]


def check_paths_reason(path: Path, ctx: Context) -> str | None:
    """Why a single resolved path may not be written, or None when it may."""
    if any(_within(path, root) for root in allowed_roots(ctx)):
        return None
    if _within(path, ctx.root):
        return f"{path} is inside the A-FC repo and needs maintenance mode"
    if ctx.active is None:
        return f"no active project: pick a project — type /afc before writing {path}"
    return f"{path} is outside the active project, so the write is blocked"


def _commands(tokens: list[str]):
    """Yield (words, redirect_targets) for each simple command in a token stream."""
    words: list[str] = []
    redirects: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _SEPARATORS:
            if words or redirects:
                yield words, redirects
            words, redirects = [], []
        elif tok in _REDIRECTS:
            if i + 1 < len(tokens):
                redirects.append(tokens[i + 1])
            i += 1
        elif tok == ">&":
            i += 1
        else:
            words.append(tok)
        i += 1
    if words or redirects:
        yield words, redirects


def _resolve(raw: str, cwd: str | None = None) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(cwd or "/") / path
    return path.resolve()


def _within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)
