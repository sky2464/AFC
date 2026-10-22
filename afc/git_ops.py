"""Delivery decisions and git wrappers.

Pure decisions (solo vs team, which branch, commit message, remote command) plus
thin subprocess wrappers around git. Every git call goes through _git.
"""

import re
import subprocess
from pathlib import Path

from afc.registry import Project

WORK_BRANCH = "afc-work"
AI_TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"
NO_IDENTITY = "This project has no git name/email yet — tell me which to use."
GITHUB_RE = re.compile(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$")


def decide_mode(recorded: str, collaborators: int, recent_authors: int) -> str:
    """Recorded solo/team wins; otherwise more than one person means team."""
    if recorded in ("solo", "team"):
        return recorded
    if collaborators > 1 or recent_authors > 1:
        return "team"
    return "solo"


def decide_branch(mode: str, default_branch: str, default_deploys: bool, protected: bool) -> str | None:
    """None means feature branch + PR (team). Solo pushes straight to default when safe."""
    if mode == "team":
        return None
    if not default_deploys and not protected:
        return default_branch
    return WORK_BRANCH


def commit_message(summary: str, ai_trailer: bool) -> str:
    if ai_trailer:
        return f"{summary}\n\n{AI_TRAILER}"
    return summary


def remote_create_command(host: str, name: str, org: str | None = None) -> list[str]:
    """Command that creates a private remote. Azure's push is done by the caller."""
    if host == "github":
        target = f"{org}/{name}" if org else name
        return ["gh", "repo", "create", target, "--private", "--source", ".", "--remote", "origin", "--push"]
    if host == "azure":
        return ["az", "repos", "create", "--name", name] + (["--org", org] if org else [])
    raise ValueError(f"unknown remote host: {host}")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50].strip("-") or "slice"


# ------------------------------------------------------------- git wrappers


def _git(code: Path, *args: str) -> str:
    """Run git in code; return stdout. Raise RuntimeError in plain words on failure."""
    try:
        done = subprocess.run(["git", *args], cwd=code, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("git is not installed.") from None
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip().splitlines()
        raise RuntimeError(f"git {args[0]} failed: {detail[-1] if detail else 'no details'}")
    return done.stdout.strip()


def commit_slice(project: Project, summary: str) -> str:
    """Stage everything in code_path and commit it as the project's identity. Return the sha."""
    if not project.git_name or not project.git_email:
        raise RuntimeError(NO_IDENTITY)
    code = Path(project.code_path)
    _git(code, "add", "-A")
    _git(
        code,
        "-c", f"user.name={project.git_name}",
        "-c", f"user.email={project.git_email}",
        "-c", "commit.gpgsign=false",
        "commit", "-m", commit_message(summary, project.ai_trailer),
    )
    return _git(code, "rev-parse", "HEAD")


def has_remote(code: Path) -> bool:
    try:
        return bool(_git(code, "remote"))
    except RuntimeError:
        return False


def remote_url(code: Path) -> str:
    try:
        return _git(code, "remote", "get-url", "origin")
    except RuntimeError:
        return ""


def github_repo(url: str) -> tuple[str, str] | None:
    match = GITHUB_RE.search(url)
    return (match.group(1), match.group(2)) if match else None


def default_branch(code: Path) -> str:
    """origin's default branch when known, else the current branch."""
    try:
        ref = _git(code, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
        return ref.split("/", 1)[1]
    except RuntimeError:
        return _git(code, "rev-parse", "--abbrev-ref", "HEAD")


def push(code: Path, branch: str) -> None:
    _git(code, "push", "origin", f"HEAD:refs/heads/{branch}")


def recent_authors(code: Path, days: int = 90) -> int:
    try:
        out = _git(code, "log", f"--since={days}.days", "--format=%ae")
    except RuntimeError:
        return 0
    return len({line.strip().lower() for line in out.splitlines() if line.strip()})
