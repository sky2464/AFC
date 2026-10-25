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
(more or fewer plugins) is still judged fairly. The target is a third less growth. Both runs must
be a whole start plus first slice: the transcript has to show `afc new`, `afc scan` and
`afc deliver` run through the Bash tool. Anything shorter is refused with a plain error, because
a session that only said "hi" would otherwise pass as a huge saving.
"""

import json
import re
import sys
from pathlib import Path

# What a whole start plus first slice does: create the project, check the slice, commit it.
STEPS = (
    ("new", "create the project"),
    ("scan", "check the slice"),
    ("deliver", "commit the slice"),
)
COMMAND = re.compile(r"\bbin/afc\s+(new|scan|deliver)\b")
# NAME=<path>/bin/afc: a session working in the project's folder keeps Flight Control's path in a variable.
AFC_VARIABLE = re.compile(r"\b(\w+)=\S*bin/afc(?=[\s;&|\"']|$)")


def _steps_in(command: str) -> set[str]:
    """The new, scan and deliver steps one command runs: `bin/afc <step>`, or `$NAME <step>` when the
    same command sets NAME to a path ending in bin/afc. Any other variable does not count."""
    found = set(COMMAND.findall(command))
    for name in AFC_VARIABLE.findall(command):
        found.update(re.findall(rf"\$(?:{name}|\{{{name}\}})\"?\s+(new|scan|deliver)\b", command))
    return found


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


def steps_reached(path) -> list[str]:
    """Which of the new, scan and deliver steps the session ran, in start-to-finish order.

    Only commands the session ran through the Bash tool count, never text that mentions them.
    """
    found: set[str] = set()
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        content = (entry.get("message") or {}).get("content") if entry.get("type") == "assistant" else None
        for item in content if isinstance(content, list) else []:
            if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Bash":
                command = (item.get("input") or {}).get("command")
                if isinstance(command, str):
                    found.update(_steps_in(command))
    return [step for step, _ in STEPS if step in found]


def _require_whole_run(path, who: str, ask: str) -> None:
    reached = steps_reached(path)
    missing = [label for step, label in STEPS if step not in reached]
    if missing:
        listed = ", ".join(missing[:-1]) + " and " + missing[-1] if len(missing) > 1 else missing[0]
        raise ValueError(f"The {who} is not a whole start plus first slice: it never got to these steps: "
                         f"{listed}. {ask}")


def compare(baseline, rerun) -> dict:
    """The re-run against the baseline on growth above each run's own floor; target: a third less."""
    _require_whole_run(rerun, "re-run", "Finish the first slice (shown, approved and committed) in one "
                                        "session, then compare again.")
    _require_whole_run(baseline, "baseline", "Use the transcript of the first live run.")
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
    try:
        result = compare(*sys.argv[1:3]) if len(sys.argv) > 2 else measure(sys.argv[1])
    except ValueError as error:
        print(json.dumps({"error": str(error)}))
        sys.exit(1)
    print(json.dumps(result, indent=2))
