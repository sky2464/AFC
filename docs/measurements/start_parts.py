"""Where a "hi" start's tokens go (FC-034 slice 1). Measurement only, not shipped.

Usage: python3 -I docs/measurements/start_parts.py [--deny "claude.ai Slack"]  (run from the folder to measure)

Runs `claude -p hi` several times, each time switching one part off, and reads the first turn's
prompt size (input + cache creation + cache read) from the first assistant message. A part's share is the full
start minus the start without it. Also prints how many tools, skills and connectors the start lists,
and with --deny, the same start with that connector name in deniedMcpServers (the restart check).
"""
import json
import subprocess
import sys

BASE = ["claude", "-p", "hi", "--output-format", "stream-json", "--verbose"]


def run(extra):
    out = subprocess.run(BASE + extra, capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
    init, usage = {}, {}
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("subtype") == "init":
            init = d
        if d.get("type") == "assistant" and not usage:
            usage = (d.get("message") or {}).get("usage") or {}  # the first turn only
    tokens = sum(usage.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    tools = init.get("tools", [])
    return {
        "tokens": tokens,
        "tools": len(tools),
        "connector_tools": sum(t.startswith("mcp__claude_ai_") for t in tools),
        "other_mcp_tools": sum(t.startswith("mcp__") and not t.startswith("mcp__claude_ai_") for t in tools),
        "skills": len(init.get("skills", [])),
        "mcp_servers": sorted(s.get("name", "") for s in init.get("mcp_servers", [])),
    }


if __name__ == "__main__":
    if "--deny" in sys.argv:
        name = sys.argv[sys.argv.index("--deny") + 1]
        settings = json.dumps({"deniedMcpServers": [{"serverName": name}]})
        print(json.dumps({"without_denial": run([]), "with_denial": run(["--settings", settings])}, indent=2))
        sys.exit()
    full = run([])
    runs = {
        "no_connectors_or_mcp": run(["--strict-mcp-config"]),
        "no_skills": run(["--disable-slash-commands"]),
        "nothing": run(["--strict-mcp-config", "--disable-slash-commands", "--tools", ""]),
    }
    share = {
        "mcp_and_connector_tools": full["tokens"] - runs["no_connectors_or_mcp"]["tokens"],
        "skill_listing": full["tokens"] - runs["no_skills"]["tokens"],
        # what is left once connectors, skills and the bare floor are taken out: built-in tools, their
        # instructions, hook text and the project's CLAUDE.md
        "builtin_tools_and_project_text": runs["no_connectors_or_mcp"]["tokens"]
        - (full["tokens"] - runs["no_skills"]["tokens"]) - runs["nothing"]["tokens"],
        "bare_floor": runs["nothing"]["tokens"],
    }
    print(json.dumps({"full": full, "runs": runs, "share_of_full_start": share}, indent=2))
