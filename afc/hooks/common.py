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
UNREADABLE_REASON = (
    "Flight Control couldn't read this command safely — "
    "split it into simpler commands or use the file tools"
)

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


_HEREDOC = re.compile(r"<<(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|\\?([A-Za-z0-9_.-]+))")


_OPENERS = (("$((", "(("), ("((", "(("), ("$[", "["), ("${", "{"))
_CLOSERS = {"((": "))", "(": ")", "[": "]", "{": "}"}


def _skip_body(text: str, i: int, pending: list) -> int:
    """From the start of a line, skip each pending heredoc body through its terminator."""
    for tabs, tag in pending:
        while i < len(text):
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            line = text[i:end].lstrip("\t") if tabs else text[i:end]
            i = end + 1
            if line == tag:
                break
    return min(i, len(text))


def strip_heredoc_bodies(command: str) -> str:
    """Drop heredoc body lines (up to and including each terminator); keep operator lines.

    One pass over the whole text; quote, escape, comment and arithmetic/brace state carry
    across newlines. `<<` counts only in plain command context; `<<<` is ignored. An
    unterminated heredoc drops the rest. If the text ends inside an unclosed quote or
    bracket construct, the original text is returned unchanged.
    """
    text = command
    out: list[str] = []
    stack: list[str] = []
    pending: list = []
    start = i = 0
    while i < len(text):
        top = stack[-1] if stack else None
        ch = text[i]
        if top == "'":
            if ch == "'":
                stack.pop()
        elif top == "$'" and ch == "\\":
            i += 1
        elif top == "$'" and ch == "'":
            stack.pop()
        elif top == "$'":
            pass
        elif top != '"' and ch == "'" and i > 0 and text[i - 1] == "$" and not _escaped(text, i - 1):
            stack.append("$'")
        elif ch == "\\":
            i += 1
        elif top == '"' and ch == '"':
            stack.pop()
        elif top in _CLOSERS and text.startswith(_CLOSERS[top], i):
            i += len(_CLOSERS[top]) - 1
            stack.pop()
        elif top in ("((", "(") and ch == "(":
            stack.append("(")
        elif top != '"' and ch in "'\"":
            stack.append(ch)
        elif any(text.startswith(op, i) for op, _ in _OPENERS if top != '"' or op[0] == "$"):
            op, kind = next(p for p in _OPENERS if text.startswith(p[0], i))
            stack.append(kind)
            i += len(op) - 1
        elif top is not None:
            pass
        elif ch == "#" and (i == 0 or text[i - 1] in " \t\n;&|()"):
            end = text.find("\n", i)
            i = (len(text) if end < 0 else end) - 1
        elif text.startswith("<<<", i):
            i += 2
        elif text.startswith("<<", i) and (match := _HEREDOC.match(text, i)):
            tag = next(g for g in match.groups()[1:] if g is not None)
            pending.append((match.group(1) == "-", tag))
            i = match.end()
            continue
        elif ch == "\n" and pending:
            out.append(text[start : i + 1])
            i = start = _skip_body(text, i + 1, pending)
            pending = []
            continue
        i += 1
    if stack:
        return command
    out.append(text[start:])
    return "".join(out)


def _escaped(text: str, i: int) -> bool:
    """True when text[i] is preceded by an odd number of backslashes."""
    count = 0
    while i - count - 1 >= 0 and text[i - count - 1] == "\\":
        count += 1
    return count % 2 == 1


def lex(command: str) -> list[str] | None:
    """Shell tokens of command with heredoc bodies dropped; None when it can't be lexed."""
    command = strip_heredoc_bodies(command)
    try:
        lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except ValueError:
        return None


def bash_write_targets(command: str, cwd: str = "/") -> list[str]:
    """Same as bash_write_targets_or_none, but unparseable input gives []."""
    return bash_write_targets_or_none(command, cwd) or []


def bash_write_targets_or_none(command: str, cwd: str = "/") -> list[str] | None:
    """Best-effort absolute paths a shell command writes to; None when it can't be lexed.

    Covers redirects (>, >>, >|, &>, >&word), tee, cp/mv/rsync (last argument or -t DIR),
    leading assignments and wrappers, `bash|sh|zsh -c`, and `cd` earlier in the chain.
    Targets with an unexpanded `$` or a backtick are skipped.
    """
    tokens = lex(command)
    if tokens is None:
        return None
    base = resolve_path(cwd)
    targets: list[str] = []
    for words, redirects in split_commands(tokens):
        for raw in redirects:
            _add_target(targets, raw, base)
        words = strip_prefix(words)
        if not words:
            continue
        name = Path(words[0]).name
        args = words[1:]
        if name == "cd":
            base = cd_base(args, base)
        elif name in _SHELLS and "-c" in args:
            index = args.index("-c")
            if index + 1 < len(args):
                inner = bash_write_targets_or_none(args[index + 1], str(base))
                if inner is None:
                    return None
                targets.extend(inner)
        else:
            for raw in _command_targets(name, args):
                _add_target(targets, raw, base)
    return targets


def _within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def split_commands(tokens: list[str]):
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


def strip_prefix(words: list[str]) -> list[str]:
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


def cd_base(args: list[str], base: Path) -> Path:
    positional = [a for a in args if not a.startswith("-")]
    if not positional:
        return Path.home()
    expanded = expand_vars(positional[0])
    if expanded is None:
        return base  # cannot know the directory; keep the current base (best effort)
    return resolve_path(expanded, str(base))


def _add_target(targets: list[str], raw: str, base: Path) -> None:
    expanded = expand_vars(raw)
    if not expanded or expanded == "/dev/null":
        return
    targets.append(str(resolve_path(expanded, str(base))))


def expand_vars(raw: str) -> str | None:
    """Expand ~ and environment variables; None when something is still unexpanded."""
    expanded = os.path.expandvars(os.path.expanduser(raw))
    if "$" in expanded or "`" in expanded:
        return None
    return expanded
