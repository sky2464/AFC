"""Delivery commands: deliver, create-remote, detect-team.

Registered into the main parser by afc.cli through register(). Each handler
returns one JSON-able dict, like every other Flight Control command.
"""

import argparse
import json
import subprocess
from pathlib import Path

from afc import git_ops
from afc.config import afc_home
from afc.registry import load_registry, save_registry

NAMES = ("deliver", "create-remote", "detect-team")
HOSTS = ("github", "azure")


def register(sub) -> None:
    p = sub.add_parser("deliver", help="commit the approved slice and push it")
    p.add_argument("--message", required=True)
    p.add_argument("--default-deploys", action="store_true")
    p.add_argument("--protected", action="store_true")
    p.set_defaults(handler=cmd_deliver)

    p = sub.add_parser("create-remote", help="create a private remote repository")
    p.add_argument("--host", required=True, choices=HOSTS)
    p.add_argument("--org")
    p.set_defaults(handler=cmd_create_remote)

    p = sub.add_parser("detect-team", help="decide solo or team for the active project")
    p.set_defaults(handler=cmd_detect_team)


def _error(message: str) -> Exception:
    from afc.cli import CliError  # late import: afc.cli imports this module

    return CliError(message)


def _active():
    from afc.cli import NO_ACTIVE

    home = afc_home()
    reg = load_registry(home)
    project = reg.active()
    if project is None:
        raise _error(NO_ACTIVE)
    return home, reg, project


def _run(cmd: list[str], code: Path) -> str:
    try:
        done = subprocess.run(cmd, cwd=code, capture_output=True, text=True)
    except FileNotFoundError:
        raise _error(f"{cmd[0]} is not installed.") from None
    if done.returncode != 0:
        lines = (done.stderr or done.stdout).strip().splitlines()
        raise _error(f"{' '.join(cmd[:3])} failed: {lines[-1] if lines else 'no details'}")
    return done.stdout


# ---------------------------------------------------------------- commands


def cmd_deliver(args: argparse.Namespace) -> dict:
    _, _, project = _active()
    code = Path(project.code_path)
    try:
        sha = git_ops.commit_slice(project, args.message)
        if not git_ops.has_remote(code):
            return {"commit": sha, "pushed": False, "pr_needed": False}
        mode = git_ops.decide_mode(project.team_mode, 0, git_ops.recent_authors(code))
        branch = git_ops.decide_branch(
            mode, git_ops.default_branch(code), args.default_deploys, args.protected
        )
        pr_needed = branch is None
        if pr_needed:
            branch = f"afc/{git_ops.slugify(args.message)}"
        git_ops.push(code, branch)
    except RuntimeError as exc:
        raise _error(str(exc)) from None
    return {"commit": sha, "pushed": True, "branch": branch, "pr_needed": pr_needed}


def cmd_create_remote(args: argparse.Namespace) -> dict:
    home, reg, project = _active()
    code = Path(project.code_path)
    if git_ops.has_remote(code):
        raise _error("This project already has a remote.")
    out = _run(git_ops.remote_create_command(args.host, project.name, args.org), code)
    if args.host == "azure":
        try:
            url = json.loads(out)["remoteUrl"]
        except (ValueError, KeyError, TypeError):
            raise _error("Azure did not say where the new repository is.") from None
        _run(["git", "remote", "add", "origin", url], code)
        _run(["git", "push", "-u", "origin", "HEAD"], code)
    reg.update(project.name, remote=args.host)
    save_registry(home, reg)
    return {"remote": args.host, "url": git_ops.remote_url(code), "private": True}


def cmd_detect_team(args: argparse.Namespace) -> dict:
    home, reg, project = _active()
    code = Path(project.code_path)
    authors = git_ops.recent_authors(code)
    repo = git_ops.github_repo(git_ops.remote_url(code))
    if repo is None:
        mode = git_ops.decide_mode("unknown", 0, authors)
        reg.update(project.name, team_mode=mode)
        save_registry(home, reg)
        return {"team_mode": mode, "recent_authors": authors, "confirm": True}
    out = _run(["gh", "api", f"repos/{repo[0]}/{repo[1]}/collaborators", "--jq", "length"], code)
    try:
        collaborators = int(out.strip())
    except ValueError:
        raise _error("GitHub did not say how many collaborators there are.") from None
    mode = git_ops.decide_mode("unknown", collaborators, authors)
    reg.update(project.name, team_mode=mode)
    save_registry(home, reg)
    return {"team_mode": mode, "collaborators": collaborators, "recent_authors": authors, "confirm": False}
