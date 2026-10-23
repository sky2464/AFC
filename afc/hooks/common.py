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

from afc.hooks.shell_text import strip_heredoc_bodies  # noqa: F401 (re-export)
from afc.hooks.shell_text import expand_known, track_assignments  # noqa: F401 (re-export)
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
_WRAPPERS = {"sudo", "env", "nohup", "command", "exec", "time", "timeout", "nice",
             "stdbuf", "ionice", "doas", "chronic", "xargs"}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish", "ash"}
_C_FLAG = re.compile(r"^-[A-Za-z]*c[A-Za-z]*$")
_SHELL_VALUE_OPTS = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
_WRAPPER_VALUE_OPTS = {
    "sudo": {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T", "-R", "--user",
             "--group", "--chdir", "--host", "--prompt", "--role", "--type", "--other-user",
             "--close-from"},
    "env": {"-u", "-C", "--unset", "--chdir"},
    "time": {"-f", "-o"},
    "exec": {"-a"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
    "nice": {"-n", "--adjustment"},
    "stdbuf": {"-i", "-o", "-e", "--input", "--output", "--error"},
    "ionice": {"-c", "-n", "-p", "-P", "-u", "--class", "--classdata"},
    "doas": {"-u", "-C"},
    "xargs": {"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a", "--arg-file", "--delimiter",
              "--max-args", "--max-procs", "--max-chars", "--max-lines", "--replace", "--eof"},
}
# Short options that take a value, for wrappers whose short options can be clustered.
_SHORT_VALUE_LETTERS = {"sudo": set("ugCDhprtU"), "env": set("uC"), "doas": set("uC")}
_WRAPPER_POSITIONALS = {"timeout": 1}  # timeout DURATION cmd
CANT_FOLLOW = object()  # shell_script result: shell code the guard can't see
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


def bash_write_targets_or_none(
    command: str, cwd: str = "/", depth: int = 0
) -> list[str] | None:
    """Best-effort absolute paths a shell command writes to; None when it can't be lexed.

    Covers redirects (>, >>, >|, &>, >&word), tee, cp/mv/rsync (last argument or -t DIR),
    leading assignments and wrappers, shell scripts (`-c`, files, source), and `cd` earlier in the chain.
    Targets with an unexpanded `$` or a backtick are skipped.
    """
    tokens = lex(command)
    if tokens is None:
        return None
    base = resolve_path(cwd)
    targets: list[str] = []
    env: dict = {}
    for words, redirects in split_commands(tokens):
        for raw in redirects:
            _add_target(targets, expand_known(raw, env), base)
        words = strip_prefix(track_assignments(words, env))
        if not words:
            continue
        name = Path(words[0]).name
        args = words[1:]
        if name == "cd":
            base = cd_base(args, base)
        elif (script := shell_script(words, base, depth)) is not None:
            if script is CANT_FOLLOW:
                return None
            inner = bash_write_targets_or_none(script, str(base), depth + 1)
            if inner is None:
                return None
            targets.extend(inner)
        else:
            for raw in _command_targets(name, args):
                _add_target(targets, raw, base)
    return targets


def _within(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


_MAX_SCRIPT_BYTES = 1_000_000
MAX_FOLLOW_DEPTH = 3


def _read_script(raw: str, base: Path):
    """Text of a script file the shell would run, or CANT_FOLLOW if it can't be read as text."""
    if "$" in raw or "`" in raw:
        return CANT_FOLLOW
    path = resolve_path(raw, str(base))
    try:
        if not path.is_file() or path.stat().st_size > _MAX_SCRIPT_BYTES:
            return CANT_FOLLOW
        data = path.read_bytes()
        if b"\0" in data:
            return CANT_FOLLOW
        return data.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return CANT_FOLLOW


def shell_script(words: list[str], base: Path | None = None, depth: int = 0):
    """Script text a command runs as shell code, CANT_FOLLOW, or None when it isn't a shell.

    `eval ARGS` gives the joined args. `source FILE` / `. FILE` and
    `SHELL [options] FILE [args]` (sh, bash, zsh, dash, ksh, fish, ash, busybox sh/ash)
    give FILE's text, resolved against `base`. `SHELL [options] -<cluster with c>
    [options] [--] SCRIPT` gives SCRIPT. Everything else — script from stdin, a missing,
    binary or >1 MB file, or following deeper than MAX_FOLLOW_DEPTH — is CANT_FOLLOW,
    which callers block. `depth` is how many scripts deep the caller already is.
    """
    name = words[0] if words[0] == "." else Path(words[0]).name
    if name == "busybox" and len(words) > 1 and words[1] in ("sh", "ash"):
        words, name = words[1:], words[1]
    if name != "eval" and name not in _SHELLS and name not in ("source", "."):
        return None
    if depth >= MAX_FOLLOW_DEPTH:
        return CANT_FOLLOW
    base = base or Path("/")
    if name == "eval":
        return " ".join(words[1:])
    if name in ("source", "."):
        return _read_script(words[1], base) if len(words) > 1 else CANT_FOLLOW
    found_c, i = False, 1
    while i < len(words):
        word = words[i]
        if word == "--":
            if i + 1 >= len(words):
                return CANT_FOLLOW
            return words[i + 1] if found_c else _read_script(words[i + 1], base)
        if word in _SHELL_VALUE_OPTS:
            i += 2
            continue
        if word.startswith("--") or (word[:1] in "-+" and len(word) > 1):
            if word[:1] == "-" and not word.startswith("--") and "s" in word:
                return CANT_FOLLOW  # -s: script comes from stdin
            found_c = found_c or bool(_C_FLAG.match(word))
            i += 1
            continue
        return word if found_c else _read_script(word, base)
    return CANT_FOLLOW


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
    """Drop leading VAR=value assignments, wrapper commands and their options.

    `env -S STRING` becomes `eval STRING ARGS`, so the split string is inspected as shell code.
    """
    i, wrapper, positionals = 0, None, 0
    while i < len(words):
        word = words[i]
        split = _env_split(wrapper, words, i)
        if split is not None:
            value, i = split
            return ["eval", value, *words[i:]]
        if _ASSIGNMENT.match(word) and wrapper not in ("xargs",):
            i += 1
        elif wrapper in _SHORT_VALUE_LETTERS and word[:1] == "-" and word[1:2] not in ("", "-"):
            cluster = _short_cluster(wrapper, words, i)
            if isinstance(cluster, tuple):
                return ["eval", cluster[0], *words[cluster[1]:]]
            i = cluster
        elif word.startswith("-") and wrapper is not None:
            i += 2 if word in _WRAPPER_VALUE_OPTS.get(wrapper, ()) else 1
        elif positionals:
            positionals -= 1
            i += 1
        elif Path(word).name in _WRAPPERS:
            wrapper = Path(word).name
            positionals = _WRAPPER_POSITIONALS.get(wrapper, 0)
            i += 1
        else:
            break
    return words[i:]


def _short_cluster(wrapper: str, words: list[str], i: int):
    """Next index after a short-option cluster at words[i], or (STRING, next) for env -S.

    A value letter takes the rest of the cluster, or the next word when it ends the cluster.
    """
    word = words[i]
    for j, ch in enumerate(word[1:], start=1):
        rest = word[j + 1:]
        if wrapper == "env" and ch == "S":
            if rest:
                return rest, i + 1
            return (words[i + 1], i + 2) if i + 1 < len(words) else ("'", i + 1)
        if ch in _SHORT_VALUE_LETTERS[wrapper]:
            return i + 1 if rest else i + 2
    return i + 1


def _env_split(wrapper, words: list[str], i: int):
    """(STRING, next index) for env's -S/--split-string at words[i], else None."""
    if wrapper != "env":
        return None
    word = words[i]
    if word in ("-S", "--split-string"):
        return (words[i + 1], i + 2) if i + 1 < len(words) else ("'", i + 1)
    if word.startswith("--split-string="):
        return word.split("=", 1)[1], i + 1
    if word.startswith("-S") and len(word) > 2:
        return word[2:], i + 1
    return None


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
