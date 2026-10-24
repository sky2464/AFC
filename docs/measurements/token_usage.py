"""Sum token usage from a Claude Code session transcript (JSONL). Measurement only, not shipped.

Usage: python3 docs/measurements/token_usage.py <transcript.jsonl>
       python3 docs/measurements/token_usage.py <baseline.jsonl> <rerun.jsonl>

Numbers (each assistant message counted once, by message id):
- peak_context: the biggest single prompt, input + cache creation + cache read (what "context" means)
- fresh_tokens: input + cache creation + output summed over turns (new work, cache reads left out)
- cache_read_tokens: summed cache reads (re-reading earlier context)
- floor_context: the first turn's prompt, before the session has done anything; the system prompt,
  tool definitions and skill listings, which Flight Control does not control
- growth: peak_context minus floor_context, what the session added by its peak (the number FC-009
  slice 4 judges)
- added_fresh_tokens: fresh_tokens without the first turn's input and cache creation

With two transcripts the result compares growth, so a run on a machine with a different floor
(more or fewer plugins) is still judged fairly. The target is a third less growth.
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
    floor = first_input = 0
    for n, u in enumerate(seen.values()):
        i = u.get("input_tokens", 0)
        cc = u.get("cache_creation_input_tokens", 0)
        cr = u.get("cache_read_input_tokens", 0)
        peak = max(peak, i + cc + cr)
        fresh += i + cc + u.get("output_tokens", 0)
        cached += cr
        if n == 0:
            floor, first_input = i + cc + cr, i + cc
    return {"turns": len(seen), "peak_context": peak, "fresh_tokens": fresh, "cache_read_tokens": cached,
            "floor_context": floor, "growth": max(peak - floor, 0),
            "added_fresh_tokens": fresh - first_input}


def compare(baseline, rerun) -> dict:
    """The re-run against the baseline on growth above each run's own floor; target: a third less."""
    before, after = measure(baseline), measure(rerun)
    if before["growth"] <= 0:
        raise ValueError("the baseline never grew above its first turn, so there is nothing to compare")
    target = before["growth"] * 2 // 3
    return {
        "floor_before": before["floor_context"], "floor_after": after["floor_context"],
        "floor_change": after["floor_context"] - before["floor_context"],
        "growth_before": before["growth"], "growth_after": after["growth"],
        "growth_change_percent": round(100 * (after["growth"] - before["growth"]) / before["growth"]),
        "growth_target": target, "target_met": after["growth"] <= target,
        "added_fresh_before": before["added_fresh_tokens"], "added_fresh_after": after["added_fresh_tokens"],
        "turns_before": before["turns"], "turns_after": after["turns"],
    }


if __name__ == "__main__":
    result = compare(*sys.argv[1:3]) if len(sys.argv) > 2 else measure(sys.argv[1])
    print(json.dumps(result, indent=2))
