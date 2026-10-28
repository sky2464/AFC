"""PreToolUse guard. Run as `sh bin/afc hook pretool`.

Exit 0 allows the tool call; exit 2 blocks it and writes the reason to stderr.
Any internal error, including a failed stdin read, blocks (fail closed).
"""

import os
import sys
from collections.abc import Callable

from afc.hooks.common import WRITE_TOOLS, Context, load_context, read_event
from afc.hooks.rules_git import check_git
from afc.hooks.rules_maintenance import check_maintenance, check_own_copy, check_undecided
from afc.hooks.rules_paths import READ_TOOLS, check_foreign_home, check_paths
from afc.hooks.rules_process import check_process
from afc.hooks.rules_resources import check_resources
from afc.hooks.rules_secrets import check_secrets

Rule = Callable[[dict, Context], str | None]

RULES: list[Rule] = [check_foreign_home, check_undecided, check_paths, check_maintenance, check_own_copy,
                     check_secrets, check_resources, check_git, check_process]

GUARDED_TOOLS = (*WRITE_TOOLS, "Bash", *READ_TOOLS)


def decide(event: dict, session_id: str | None = None) -> str | None:
    """The reason this tool call must be blocked, or None to allow it. Shared by the Claude Code
    hook and `afc guard`, so every tool gets the same answer."""
    if event.get("tool_name") not in GUARDED_TOOLS:
        return None
    ctx = load_context(session_id if session_id is not None else event.get("session_id"))
    for rule in RULES:
        reason = rule(event, ctx)
        if reason:
            return reason
    return None


def _cursor_chat(event: dict) -> str | None:
    """The chat ID when Cursor sent this event through the Claude Code hook, else None (FC-057).

    Cursor runs this hook on its own edits but sets no CURSOR_CONVERSATION_ID, so the chat is only
    known by Cursor's fields in the message (Claude Code sends neither)."""
    if "cursor_version" not in event and "conversation_id" not in event:
        return None
    chat = event.get("conversation_id") or event.get("session_id")
    return chat.strip() or None if isinstance(chat, str) else None


def main(stdin_text: str, stderr) -> int:
    try:
        event = read_event(stdin_text)
        chat = _cursor_chat(event)
        if chat:
            # Mark the chat as Cursor's so the branch-wide /afc mm applies, as in FC-054.
            os.environ["CURSOR_CONVERSATION_ID"] = chat
        reason = decide(event, chat)
        if reason:
            print(f"Flight Control blocked: {reason}", file=stderr)
            return 2
        return 0
    except Exception as exc:  # fail closed on any internal error
        print(f"Flight Control guard error: {exc}", file=stderr)
        return 2


def run(stderr) -> int:
    """Read the hook event from stdin and decide. Read errors also fail closed."""
    try:
        return main(sys.stdin.read(), stderr)
    except Exception as exc:
        print(f"Flight Control guard error: {exc}", file=stderr)
        return 2


if __name__ == "__main__":
    sys.exit(run(sys.stderr))
