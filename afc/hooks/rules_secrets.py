"""Secret rule: block write-tool content that contains a secret."""

from afc.hooks.common import WRITE_TOOLS, Context, string_values
from afc.secrets import find_secrets


def check_secrets(event: dict, ctx: Context) -> str | None:
    """Reason naming the matched pattern(s), never the value; None when clean."""
    if event.get("tool_name") not in WRITE_TOOLS:
        return None
    names: list[str] = []
    tool_input = event.get("tool_input")
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    filename = raw if isinstance(raw, str) else None
    for text in string_values(tool_input):
        names.extend(n for n in find_secrets(text, filename) if n not in names)
    if not names:
        return None
    return f"this looks like a secret ({', '.join(names)}) — use an environment variable instead"
