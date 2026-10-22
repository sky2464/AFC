"""Secret rule: block write-tool content that contains a secret."""

from afc.hooks.common import WRITE_TOOLS, Context, string_values
from afc.secrets import find_secrets


def check_secrets(event: dict, ctx: Context) -> str | None:
    """Reason naming the matched pattern(s), never the value; None when clean."""
    if event.get("tool_name") not in WRITE_TOOLS:
        return None
    names: list[str] = []
    for text in string_values(event.get("tool_input")):
        names.extend(n for n in find_secrets(text) if n not in names)
    if not names:
        return None
    return f"this looks like a secret ({', '.join(names)}) — use an environment variable instead"
