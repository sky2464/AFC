"""Sum token usage from a Claude Code session transcript (JSONL). Measurement only, not shipped.

Usage: python3 docs/measurements/token_usage.py <transcript.jsonl>

Numbers (each assistant message counted once, by message id):
- peak_context: the biggest single prompt, input + cache creation + cache read (what "context" means)
- fresh_tokens: input + cache creation + output summed over turns (new work, cache reads left out)
- cache_read_tokens: summed cache reads (re-reading earlier context)
"""

import json
import sys
from pathlib import Path


def measure(path) -> dict:
    seen: dict[str, dict] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "assistant":
            continue
        message = entry.get("message") or {}
        usage = message.get("usage")
        if message.get("id") and isinstance(usage, dict):
            seen[message["id"]] = usage
    peak = fresh = cached = 0
    for u in seen.values():
        i = u.get("input_tokens", 0)
        cc = u.get("cache_creation_input_tokens", 0)
        cr = u.get("cache_read_input_tokens", 0)
        peak = max(peak, i + cc + cr)
        fresh += i + cc + u.get("output_tokens", 0)
        cached += cr
    return {"turns": len(seen), "peak_context": peak, "fresh_tokens": fresh, "cache_read_tokens": cached}


if __name__ == "__main__":
    print(json.dumps(measure(sys.argv[1]), indent=2))
