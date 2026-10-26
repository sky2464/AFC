"""Guard command: guard --shell CMD | --write PATH | --read PATH | --staged | --since REF.

Registered into the main parser by afc.cli through register(). It asks the same rules the Claude Code
PreToolUse hook uses whether one action is allowed, so another tool's hook or a commit check can call
it. Allowed exits 0; blocked prints the reason and exits 2, like the hook.

--staged and --since are the commit-time floor for tools with no hooks: they run the secret rule over
the files a commit or pull request changes. Only names are reported, never the matched values.
"""

import argparse
import os
import subprocess

from afc.config import current_session

NAMES = ("guard",)


def register(sub) -> None:
    p = sub.add_parser("guard", help="ask whether one action is allowed (for other tools' hooks)")
    what = p.add_mutually_exclusive_group(required=True)
    what.add_argument("--shell", metavar="COMMAND", help="a shell command about to run")
    what.add_argument("--write", metavar="PATH", help="a file about to be written or edited")
    what.add_argument("--read", metavar="PATH", help="a file about to be read")
    what.add_argument("--staged", action="store_true", help="check the files staged for commit")
    what.add_argument("--since", metavar="REF", help="check the files changed from REF to HEAD")
    p.add_argument("--cwd", default=None, help="folder the action runs in (default: here)")
    p.set_defaults(handler=cmd_guard)


def build_event(args: argparse.Namespace) -> dict:
    cwd = args.cwd or os.getcwd()
    if args.shell is not None:
        tool, tool_input = "Bash", {"command": args.shell}
    elif args.write is not None:
        tool, tool_input = "Write", {"file_path": args.write}
    else:
        tool, tool_input = "Read", {"file_path": args.read}
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input, "cwd": cwd}


MAX_FILE_BYTES = 1024 * 1024


def _git(args: list[str], cwd: str) -> bytes:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=60)
    if done.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {done.stderr.decode(errors='replace').strip()}")
    return done.stdout


def changed_files(args: argparse.Namespace, cwd: str) -> list[tuple[str, str]]:
    """(path, text) for each added or changed text file: the staged copy, or the one at HEAD."""
    if args.staged:
        listing = _git(["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], cwd)
        source = ":"
    else:
        listing = _git(["diff", "--name-only", "--diff-filter=ACMR", "-z", f"{args.since}...HEAD"], cwd)
        source = "HEAD:"
    found = []
    for path in filter(None, listing.decode(errors="replace").split("\0")):
        blob = _git(["show", source + path], cwd)
        if len(blob) <= MAX_FILE_BYTES and b"\0" not in blob:
            found.append((path, blob.decode(errors="replace")))
    return found


def check_changed(args: argparse.Namespace) -> str | None:
    from afc.hooks.rules_secrets import check_secrets

    cwd = args.cwd or os.getcwd()
    bad = []
    for path, text in changed_files(args, cwd):
        event = {"tool_name": "Write", "tool_input": {"file_path": path, "content": text}}
        reason = check_secrets(event, None)  # the rule reads only the event
        if reason:
            bad.append(f"{path}: {reason}")
    return "; ".join(bad) or None


def cmd_guard(args: argparse.Namespace) -> dict:
    from afc.hooks.pretool import decide

    try:
        if args.staged or args.since:
            reason = check_changed(args)
        else:
            reason = decide(build_event(args), current_session())
    except Exception as exc:  # fail closed, like the hook
        reason = f"the guard could not decide ({exc})"
    if reason:
        return {"allow": False, "reason": reason, "exit_code": 2}
    return {"allow": True}
