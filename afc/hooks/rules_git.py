"""Git and publication rule: dangerous git, making things public, production deploys,
and a secret scan of what `git commit` is about to record.

Matching is per simple command on shell tokens (heredoc bodies dropped), so text that
only mentions a blocked phrase — a commit message, an echo — is not matched.
"""

import re
import subprocess
from pathlib import Path

from afc.hooks.common import (
    CANT_FOLLOW,
    UNREADABLE_REASON,
    Context,
    cd_base,
    expand_vars,
    lex,
    resolve_path,
    shell_script,
    split_commands,
    strip_prefix,
)
from afc.secrets import find_secrets

GIT_REASON = "this git command can lose work or rewrite history — run it yourself if you mean it"
PUBLIC_REASON = "this would make something public — repos stay private; change it yourself if you mean it"
DEPLOY_REASON = "this looks like a production deploy — run it yourself if you mean it"
GIT_MISSING_REASON = "Flight Control couldn't check this commit for secrets because git didn't run"

# (tool, words that must all appear after it) — one deploy verb each.
PROD_DEPLOY = [
    ("terraform", ("apply",)), ("kubectl", ("apply",)), ("kubectl", ("delete",)),
    ("kubectl", ("rollout",)), ("helm", ("install",)), ("helm", ("upgrade",)),
    ("az", ("webapp", "deploy")), ("az", ("deployment",)), ("aws", ("deploy",)),
    ("gh", ("workflow", "run")), ("docker", ("push",)),
]
PROD_TOKEN = re.compile(r"\b(prod|production|prd)\b")

_GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}
_GIT_LOCATION_OPTS = {"-C", "--git-dir", "--work-tree"}
_COMMIT_VALUE_SHORT = set("mFCct")
_COMMIT_VALUE_LONG = {"--message", "--file", "--reuse-message", "--reedit-message", "--author",
                      "--date", "--template", "--fixup", "--squash", "--trailer", "--cleanup",
                      "--pathspec-from-file"}
_REBASE_SAFE = {"--abort", "--continue", "--quit"}
_WHOLE_TREE = {".", "./", ":/", "*"}
_DIFF = ("-U0", "--no-color", "--no-ext-diff", "--no-textconv")


def simple_commands(
    command: str, cwd: str, depth: int = 0
) -> list[tuple[list[str], Path]] | None:
    """(words, directory) for each simple command, following `cd` and `sh -c`; None if unlexable."""
    tokens = lex(command)
    if tokens is None:
        return None
    base = resolve_path(cwd)
    out: list[tuple[list[str], Path]] = []
    for words, _ in split_commands(tokens):
        words = strip_prefix(words)
        while words and Path(words[0]).name == "xargs":
            words = strip_prefix(words[1:])
        if not words:
            continue
        name = Path(words[0]).name
        if name == "cd":
            base = cd_base(words[1:], base)
        elif (script := shell_script(words, base, depth)) is not None:
            if script is CANT_FOLLOW:
                return None
            inner = simple_commands(script, str(base), depth + 1)
            if inner is None:
                return None
            out.extend(inner)
        else:
            out.append((words, base))
    return out


def parse_git(words: list[str]) -> tuple[list[str], str, list[str]] | None:
    """(location options, subcommand, args) for a git command; None when it isn't one."""
    if Path(words[0]).name != "git":
        return None
    location: list[str] = []
    i = 1
    while i < len(words) and words[i].startswith("-"):
        opt = words[i]
        key = opt.split("=", 1)[0]
        takes_value = opt in _GIT_VALUE_OPTS
        if key in _GIT_LOCATION_OPTS:
            location.extend(words[i : i + 2] if takes_value else [opt])
        i += 2 if takes_value else 1
    if i >= len(words):
        return location, "", []
    return location, words[i], words[i + 1 :]


def _flags(args: list[str]) -> tuple[set[str], set[str], list[str]]:
    shorts = {c for a in args if re.fullmatch(r"-[A-Za-z]+", a) for c in a[1:]}
    longs = {a.split("=", 1)[0] for a in args if a.startswith("--")}
    positional = [a for a in args if not a.startswith("-")]
    return shorts, longs, positional


def dangerous_git(sub: str, args: list[str]) -> bool:
    shorts, longs, positional = _flags(args)
    if sub == "push":
        return bool(longs & {"--force", "--mirror", "--delete", "--force-with-lease"}
                    or shorts & {"f", "d"}
                    or any(p.startswith(("+", ":")) for p in positional))
    if sub == "reset":
        return "--hard" in longs
    if sub == "clean":
        return "f" in shorts or "--force" in longs
    if sub == "branch":
        force = "f" in shorts or "--force" in longs
        return "D" in shorts or (force and ("d" in shorts or "--delete" in longs))
    if sub in ("checkout", "restore"):
        return any(a in _WHOLE_TREE for a in args)
    if sub == "rebase":
        return not (longs & _REBASE_SAFE)
    if sub in ("filter-branch", "filter-repo"):
        return True
    if sub == "commit":
        return "--amend" in longs
    return False


def publication(words: list[str]) -> bool:
    for i, w in enumerate(words):
        if w in ("--public", "--visibility=public"):
            return True
        if w == "--visibility" and i + 1 < len(words) and words[i + 1] == "public":
            return True
    if Path(words[0]).name == "gh" and words[1:3] == ["repo", "create"]:
        return "--private" not in words
    if Path(words[0]).name == "gh" and words[1:3] == ["repo", "edit"]:
        return any(w.startswith("--visibility") for w in words)
    return False


def prod_deploy(words: list[str]) -> bool:
    name, rest = Path(words[0]).name, words[1:]
    verb = any(name == tool and all(v in rest for v in need) for tool, need in PROD_DEPLOY)
    return verb and any(PROD_TOKEN.search(w) for w in rest)


def added_lines(diff: str) -> str:
    """Added content lines of a unified diff; file headers are skipped."""
    lines: list[str] = []
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("diff "):
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines)


def _git(location: list[str], base: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *location, *args], cwd=base, capture_output=True, text=True)


def staged_diff(repo: Path, location: list[str] | None = None) -> str:
    """Added lines of `git diff --cached -U0` in repo."""
    result = _git(location or [], repo, "diff", "--cached", *_DIFF)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, "git diff --cached")
    return added_lines(result.stdout)


def unstaged_diff(repo: Path, location: list[str], paths: list[str]) -> str:
    """Added lines of tracked, unstaged changes (limited to paths when given)."""
    result = _git(location, repo, "diff", *_DIFF, "--", *paths)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, "git diff")
    return added_lines(result.stdout)


def scan_commit_text(text: str) -> str | None:
    """Reason to block a commit whose added lines are text, or None. Task 8 extends this."""
    names = find_secrets(text)
    if names:
        return (f"the changes being committed look like they contain a secret ({', '.join(names)}) "
                "— remove it and use an environment variable instead")
    return None


def commit_scope(args: list[str]) -> tuple[bool, list[str]]:
    """(commits unstaged tracked changes too, pathspecs) for `git commit` args."""
    extra, paths, i = False, [], 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            paths.extend(args[i + 1 :])
            break
        if arg.startswith("--"):
            key = arg.split("=", 1)[0]
            extra = extra or key in ("--all", "--include", "--only")
            if key in _COMMIT_VALUE_LONG and "=" not in arg:
                i += 1
        elif arg.startswith("-") and len(arg) > 1:
            for j, ch in enumerate(arg[1:], start=1):
                extra = extra or ch in "aio"
                if ch in _COMMIT_VALUE_SHORT:
                    if j == len(arg) - 1:
                        i += 1
                    break
        else:
            paths.append(arg)
        i += 1
    return extra or bool(paths), paths


def _scan_commit(location: list[str], base: Path, args: list[str], fallback: str) -> str | None:
    expanded = []
    for value in location:
        value = expand_vars(value)
        if value is None:
            return UNREADABLE_REASON
        expanded.append(value)
    if not base.is_dir():
        base = resolve_path(fallback)  # an earlier cd failed; the shell stays where it was
    if not base.is_dir():
        return UNREADABLE_REASON
    try:
        if _git(expanded, base, "rev-parse", "--is-inside-work-tree").returncode != 0:
            return None  # not a repo: git itself will refuse the commit
        text = staged_diff(base, expanded)
        extra, paths = commit_scope(args)
        if extra:
            text += "\n" + unstaged_diff(base, expanded, paths)
    except (OSError, subprocess.CalledProcessError):
        return GIT_MISSING_REASON
    return scan_commit_text(text)


def check_git(event: dict, ctx: Context) -> str | None:
    """Reason naming the category that blocks this Bash command, or None."""
    if event.get("tool_name") != "Bash":
        return None
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command:
        return None
    commands = simple_commands(command, event.get("cwd") or "/")
    if commands is None:
        return UNREADABLE_REASON
    commits = []
    for words, base in commands:
        git = parse_git(words)
        if git and dangerous_git(git[1], git[2]):
            return GIT_REASON
        if publication(words):
            return PUBLIC_REASON
        if prod_deploy(words):
            return DEPLOY_REASON
        if git and git[1] == "commit":
            commits.append((git[0], base, git[2]))
        elif not git and "git" in words and "commit" in words[words.index("git") :]:
            return UNREADABLE_REASON  # a commit we can't locate, e.g. find -exec git commit
    for location, base, args in commits:
        reason = _scan_commit(location, base, args, event.get("cwd") or "/")
        if reason:
            return reason
    return None
