"""Delivery commands: deliver, create-remote, detect-team.

Registered into the main parser by afc.cli through register(). Each handler
returns one JSON-able dict, like every other Flight Control command.
"""

import argparse
import json
import subprocess
from pathlib import Path

from afc import git_ops
from afc.config import afc_home, afc_root, current_session, maintain_enabled
from afc.registry import Project, load_registry, save_registry

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
    p.add_argument("--project")
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


def _fc_identity(home) -> tuple[str, str, bool]:
    """Git name/email for a Flight Control commit: active project, else this repo's git config."""
    active = load_registry(home).active()
    if active and active.git_name and active.git_email:
        return active.git_name, active.git_email, active.ai_trailer
    root = afc_root()
    try:
        name = git_ops._git(root, "config", "user.name")
        email = git_ops._git(root, "config", "user.email")
    except RuntimeError:
        name, email = "", ""
    return name, email, False


def _deliver_flight_control(args: argparse.Namespace) -> dict:
    """Commit dirty files in the A-FC folder itself (FC-054). Never touches the active project.

    Flight Control is built on `dev` (not `main`), so this commits and optionally pushes the
    current branch as-is — no switch to the default branch.
    """
    home = afc_home()
    root = afc_root()
    name, email, trailer = _fc_identity(home)
    if not name or not email:
        raise _error("Set git user.name and user.email (or an active project's git identity) "
                     "before delivering Flight Control.")
    project = Project(
        name="flight-control",
        code_path=str(root),
        workspace_path=str(home),
        git_name=name,
        git_email=email,
        ai_trailer=trailer,
        team_mode="solo",
        remote="github" if git_ops.has_remote(root) else "none",
    )
    try:
        branch = git_ops.current_branch(root)
        if branch in ("", "HEAD"):
            raise RuntimeError("Flight Control's copy is not on a branch — switch to dev first.")
        if branch == "main":
            raise RuntimeError("Flight Control is not delivered on main — switch to dev first.")
        sha = git_ops.commit_slice(project, args.message)
        if not git_ops.has_remote(root):
            return {"commit": sha, "pushed": False, "pr_needed": False, "brief": "skipped",
                    "target": "flight-control", "branch": branch}
        git_ops.push(root, branch)
    except RuntimeError as exc:
        raise _error(str(exc)) from None
    return {
        "commit": sha,
        "pushed": True,
        "branch": branch,
        "pr_needed": False,
        "brief": "skipped",
        "target": "flight-control",
    }


def cmd_deliver(args: argparse.Namespace) -> dict:
    if maintain_enabled(afc_home(), current_session()):
        return _deliver_flight_control(args)
    _, _, project = _active()
    code = Path(project.code_path)
    try:
        if not git_ops.has_remote(code):
            result = {"commit": git_ops.commit_slice(project, args.message), "pushed": False, "pr_needed": False}
            result["brief"] = _refresh_brief(project)
            return result
        git_ops.check_ready(project)
        default = git_ops.default_branch(code)
        mode = git_ops.decide_mode(project.team_mode, 0, git_ops.recent_authors(code))
        branch = git_ops.decide_branch(mode, default, args.default_deploys, args.protected)
        pr_needed = branch is None
        if pr_needed:
            branch = f"afc/{git_ops.slugify(args.message)}"
            git_ops.switch_to(code, branch, git_ops.upstream_base(code, default))
        elif branch == git_ops.WORK_BRANCH:
            git_ops.switch_to(code, branch)
        elif git_ops.current_branch(code) != default:
            raise RuntimeError(
                f"You are on branch {git_ops.current_branch(code)}, not {default} — "
                f"switch to {default} first, then deliver again."
            )
        sha = git_ops.commit_slice(project, args.message)
        git_ops.push(code, branch)
    except RuntimeError as exc:
        raise _error(str(exc)) from None
    return {
        "commit": sha,
        "pushed": True,
        "branch": branch,
        "pr_needed": pr_needed,
        "brief": _refresh_brief(project),
    }


def _refresh_brief(project) -> dict:
    from afc.context_brief import refresh

    return refresh(project.workspace_path, profile=project.profile or "personal")


AZ_NO_DEFAULTS = (
    "Azure DevOps does not know which organization and project to use yet — run "
    "az devops configure --defaults organization=<url> project=<name>, or tell me both."
)


def _azure_project(args: argparse.Namespace, code: Path) -> str:
    """The Azure project to create the repo in; refuse when it is public."""
    project = args.project
    if not project:
        listing = _run(["az", "devops", "configure", "--list"], code)
        for line in listing.splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "project" and value.strip():
                project = value.strip()
    if not project:
        raise _error(AZ_NO_DEFAULTS)
    cmd = ["az", "devops", "project", "show", "--project", project]
    try:
        info = json.loads(_run(cmd + (["--org", args.org] if args.org else []), code))
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise _error("Azure did not say whether the project is private.") from None
        raise _error(f"{AZ_NO_DEFAULTS} ({exc})") from None
    if str(info.get("visibility", "")).lower() != "private":
        raise _error(
            f"Azure project {project} is public, so a new repository there would be public. "
            "Pick a private project instead."
        )
    return project


def cmd_create_remote(args: argparse.Namespace) -> dict:
    home, reg, project = _active()
    code = Path(project.code_path)
    if git_ops.has_remote(code):
        raise _error("This project already has a remote.")
    cmd = git_ops.remote_create_command(args.host, project.name, args.org)
    if args.host == "azure":
        cmd += ["--project", _azure_project(args, code)]
    out = _run(cmd, code)
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
    if project.team_mode in ("solo", "team"):
        return {"team_mode": project.team_mode, "recent_authors": authors, "confirm": False}
    repo = git_ops.github_repo(git_ops.remote_url(code))
    if repo is None:
        mode = git_ops.decide_mode("unknown", 0, authors)
        reg.update(project.name, team_mode=mode)
        save_registry(home, reg)
        # A personal project nobody else has committed to needs no question.
        sure = project.profile == "personal" and authors <= 1
        return {"team_mode": mode, "recent_authors": authors, "confirm": not sure}
    out = _run(["gh", "api", f"repos/{repo[0]}/{repo[1]}/collaborators", "--jq", "length"], code)
    try:
        collaborators = int(out.strip())
    except ValueError:
        raise _error("GitHub did not say how many collaborators there are.") from None
    mode = git_ops.decide_mode("unknown", collaborators, authors)
    reg.update(project.name, team_mode=mode)
    save_registry(home, reg)
    return {"team_mode": mode, "collaborators": collaborators, "recent_authors": authors, "confirm": False}
