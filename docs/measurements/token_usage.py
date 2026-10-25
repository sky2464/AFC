"""Sum token usage from a Claude Code session transcript (JSONL). Measurement only, not shipped.

Usage: python3 docs/measurements/token_usage.py <transcript.jsonl>
       python3 docs/measurements/token_usage.py <control.jsonl> <rerun.jsonl>
       python3 docs/measurements/token_usage.py --parts <transcript.jsonl>   (growth by part, FC-017)

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
(more or fewer plugins) is still judged fairly. The control is a whole run of the same flow made on
`dev` before the change, so both runs build the same kind of first slice; the target is 10% less
growth than the control's. Both runs must be a whole start plus first slice: the transcript has to show `afc new`, `afc scan` and
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
# The re-run passes when its growth is at most this share of the control's (10% less). A third less
# was the first target and is out of reach by trimming alone on a tested first slice (FC-009).
TARGET_SHARE = (9, 10)
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


PARTS = ("code_and_tests", "replies", "skill_text", "plan_and_spec_edits", "files_read", "other")
PLAN_OR_SPEC = re.compile(r"(^|/)(docs/specs/|docs/master-plan|plan[^/]*\.md$|specs?/[^/]*\.md$)")
SKILL_FILE = re.compile(r"(^|/)skills/")


def _part_of(content) -> str:
    """The part one turn's tool calls belong to. Plan and spec edits first, then skill text, then
    code and tests; reading comes next, any other tool is "other", and a turn with no tool call is
    the model's reply."""
    found: set[str] = set()
    for item in content if isinstance(content, list) else []:
        if not isinstance(item, dict) or item.get("type") != "tool_use":
            continue
        name, args = item.get("name"), item.get("input") or {}
        path = str(args.get("file_path") or args.get("path") or "")
        if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            found.add("plan_and_spec_edits" if PLAN_OR_SPEC.search(path) else "code_and_tests")
        elif name == "Skill" or (name == "Read" and SKILL_FILE.search(path)):
            found.add("skill_text")
        elif name in ("Read", "Grep", "Glob"):
            found.add("files_read")
        else:
            found.add("other")
    for part in ("plan_and_spec_edits", "skill_text", "code_and_tests", "files_read", "other"):
        if part in found:
            return part
    return "replies"


def breakdown(path) -> dict:
    """Growth by part. A turn's prompt holds what the turn before it added (its reply, its tool
    call and the result), so each jump in the prompt is credited to the part of the turn before it.
    Jumps are counted up to the first turn with the peak prompt, so the parts add up to `growth`."""
    turns: dict[str, dict] = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") or {}
        if entry.get("type") != "assistant" or not message.get("id") or not isinstance(message.get("usage"), dict):
            continue
        turn = turns.setdefault(message["id"], {"content": []})
        turn["usage"] = message["usage"]
        if isinstance(message.get("content"), list):
            turn["content"].extend(message["content"])
    order = list(turns.values())
    sizes = [sum(t["usage"].get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                 "cache_read_input_tokens")) for t in order]
    result = dict.fromkeys(PARTS, 0)
    if sizes:
        peak_at = sizes.index(max(sizes))
        for n in range(1, peak_at + 1):
            result[_part_of(order[n - 1]["content"])] += sizes[n] - sizes[n - 1]
    result["growth"] = sum(result.values())
    return result


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


def compare(control, rerun) -> dict:
    """The re-run against a like-for-like control on growth above each run's own floor; target: 10% less."""
    _require_whole_run(rerun, "re-run", "Finish the first slice (shown, approved and committed) in one "
                                        "session, then compare again.")
    _require_whole_run(control, "control", "Use a whole run of the same flow on dev before the change, "
                                           "made the same day.")
    before, after = measure(control), measure(rerun)
    if before["growth"] <= 0:
        raise ValueError("the control never grew above its first turn, so there is nothing to compare")
    target = before["growth"] * TARGET_SHARE[0] // TARGET_SHARE[1]
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
        if sys.argv[1] == "--parts":
            result = breakdown(sys.argv[2])
        else:
            result = compare(*sys.argv[1:3]) if len(sys.argv) > 2 else measure(sys.argv[1])
    except ValueError as error:
        print(json.dumps({"error": str(error)}))
        sys.exit(1)
    print(json.dumps(result, indent=2))
