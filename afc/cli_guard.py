"""Guard command: guard --shell CMD | --write PATH | --read PATH.

Registered into the main parser by afc.cli through register(). It asks the same rules the Claude Code
PreToolUse hook uses whether one action is allowed, so another tool's hook or a commit check can call
it. Allowed exits 0; blocked prints the reason and exits 2, like the hook.
"""

import argparse
import os

from afc.config import current_session

NAMES = ("guard",)


def register(sub) -> None:
    p = sub.add_parser("guard", help="ask whether one action is allowed (for other tools' hooks)")
    what = p.add_mutually_exclusive_group(required=True)
    what.add_argument("--shell", metavar="COMMAND", help="a shell command about to run")
    what.add_argument("--write", metavar="PATH", help="a file about to be written or edited")
    what.add_argument("--read", metavar="PATH", help="a file about to be read")
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


def cmd_guard(args: argparse.Namespace) -> dict:
    from afc.hooks.pretool import decide

    try:
        reason = decide(build_event(args), current_session())
    except Exception as exc:  # fail closed, like the hook
        reason = f"the guard could not decide ({exc})"
    if reason:
        return {"allow": False, "reason": reason, "exit_code": 2}
    return {"allow": True}
