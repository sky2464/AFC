"""PreToolUse guard. Run as `python3 -m afc.hooks.pretool`.

Exit 0 allows the tool call; exit 2 blocks it and writes the reason to stderr.
Any internal error, including a failed stdin read, blocks (fail closed).
"""

import sys
from collections.abc import Callable

from afc.hooks.common import WRITE_TOOLS, Context, load_context, read_event
from afc.hooks.rules_paths import check_paths

Rule = Callable[[dict, Context], str | None]

RULES: list[Rule] = [check_paths]

GUARDED_TOOLS = (*WRITE_TOOLS, "Bash")


def main(stdin_text: str, stderr) -> int:
    try:
        event = read_event(stdin_text)
        if event.get("tool_name") not in GUARDED_TOOLS:
            return 0
        ctx = load_context()
        for rule in RULES:
            reason = rule(event, ctx)
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
