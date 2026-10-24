"""Process rule: stop a program by its process ID, never by name or pattern.

`pkill` and `killall` match by name, so a pattern like `next dev` also stops other people's servers.
`kill <pid>` stays allowed. Matching is per simple command, so text that only mentions the word
(an echo, a commit message) is not matched. A command that can't be read is left to the other
rules, which already refuse it.
"""

from pathlib import Path

from afc.hooks.common import Context
from afc.hooks.rules_git import simple_commands

PATTERN_KILLS = ("pkill", "killall")
PROCESS_REASON = ("this stops programs by name or pattern, which can also stop other people's "
                  "servers — stop the one you started by its process ID (kill <pid>)")


def check_process(event: dict, ctx: Context) -> str | None:
    """Return a block reason for `pkill`/`killall`, else None."""
    if event.get("tool_name") != "Bash":
        return None
    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or not command:
        return None
    for words, _ in simple_commands(command, event.get("cwd") or "/") or []:
        if Path(words[0]).name in PATTERN_KILLS:
            return PROCESS_REASON
    return None
