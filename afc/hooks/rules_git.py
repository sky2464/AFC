"""Git and publication rule: dangerous git, making things public, production deploys,
and a secret scan of staged changes on `git commit`."""

import re
import shlex
import subprocess
from pathlib import Path

from afc.hooks.common import (
    UNREADABLE_REASON,
    Context,
    _cd_base,
    _commands,
    _expand,
    _strip_prefix,
    resolve_path,
    strip_heredoc_bodies,
)
from afc.secrets import find_secrets

DANGEROUS_GIT = [
    r"git push .*(--force|-f\b|--mirror|--delete)",
    r"git push .*\+\S",
    r"git reset --hard",
    r"git clean -[a-z]*f",
    r"git branch -D",
    r"git checkout \.",
    r"git restore \.",
    r"git rebase",
    r"git filter-branch",
    r"git filter-repo",
    r"git commit .*--amend",
]
PUBLICATION = [
    r"gh repo create(?!.*--private)",
    r"--public\b",
    r"--visibility[ =]public",
    r"gh repo edit .*visibility",
    r"az devops project create .*--visibility public",
]
DEPLOY_VERBS = [
    r"terraform apply",
    r"kubectl (apply|delete|rollout)",
    r"helm (install|upgrade)",
    r"az webapp deploy",
    r"az deployment",
    r"aws \S+ deploy",
    r"gh workflow run",
    r"docker push",
]
PROD_TOKEN = r"\b(prod|production|prd)\b"

GIT_REASON = "this git command can lose work or rewrite history — run it yourself if you mean it"
PUBLIC_REASON = "this would make something public — repos stay private; change it yourself if you mean it"
DEPLOY_REASON = "this looks like a production deploy — run it yourself if you mean it"
GIT_MISSING_REASON = "Flight Control couldn't check this commit for secrets because git didn't run"

# `git -C path` / `git -c key=value` options between `git` and its subcommand.
_GIT_OPTS = re.compile(r"\bgit((?:\s+-[Cc]\s+\S+)+)(?=\s)")


def _normalize(command: str) -> str:
    return _GIT_OPTS.sub("git", command)


def _any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def staged_diff(repo: Path) -> str:
    """Added lines of `git -C repo diff --cached -U0`, joined by newlines."""
    out = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "-U0", "--no-color"],
        capture_output=True, text=True, check=True,
    ).stdout
    return "\n".join(
        line[1:] for line in out.splitlines() if line.startswith("+") and not line.startswith("+++")
    )


def _commit_repos(command: str, cwd: str) -> list[Path] | None:
    """Directories each `git ... commit` in the command runs in; None when it can't be lexed."""
    try:
        lexer = shlex.shlex(strip_heredoc_bodies(command).replace("\n", " ; "),
                            posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return None
    base = resolve_path(cwd)
    repos: list[Path] = []
    for words, _ in _commands(tokens):
        words = _strip_prefix(words)
        if not words:
            continue
        if Path(words[0]).name == "cd":
            base = _cd_base(words[1:], base)
            continue
        if Path(words[0]).name != "git":
            continue
        repo, i = base, 1
        while i + 1 < len(words) and words[i] in ("-C", "-c"):
            if words[i] == "-C":
                expanded = _expand(words[i + 1])
                if expanded is None:
                    return None
                repo = resolve_path(expanded, str(repo))
            i += 2
        if i < len(words) and words[i] == "commit":
            repos.append(repo)
    return repos


def _is_repo(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def _scan_commit(command: str, cwd: str) -> str | None:
    repos = _commit_repos(command, cwd)
    if repos is None:
        return UNREADABLE_REASON
    try:
        for repo in repos:
            if not repo.is_dir() or not _is_repo(repo):
                continue  # not a repo: git itself will refuse the commit
            names = find_secrets(staged_diff(repo))
            if names:
                return (f"the staged changes look like they contain a secret ({', '.join(names)}) "
                        "— remove it and use an environment variable instead")
    except (OSError, subprocess.CalledProcessError):
        return GIT_MISSING_REASON
    return None


def check_git(event: dict, ctx: Context) -> str | None:
    """Reason naming the category that blocks this Bash command, or None."""
    if event.get("tool_name") != "Bash":
        return None
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command:
        return None
    text = _normalize(command)
    if _any(DANGEROUS_GIT, text):
        return GIT_REASON
    if _any(PUBLICATION, text):
        return PUBLIC_REASON
    if _any(DEPLOY_VERBS, text) and re.search(PROD_TOKEN, text):
        return DEPLOY_REASON
    if re.search(r"\bgit\b.*\bcommit\b", text):
        return _scan_commit(command, event.get("cwd") or "/")
    return None
