"""Hook adapters for tools other than Claude Code (FC-051). Run as `sh bin/afc hook adapter <tool>`.

Each tool sends its own hook payload and wants its own deny reply. This turns the payload into the
event the PreToolUse rules already read, asks them (afc.hooks.pretool.decide), and answers in the
tool's words. Anything it can't read blocks (fail closed), as the Claude Code hook does.

What each tool can block before it happens (checked 2026-10-26): Cursor shell commands and file
reads; Codex shell commands and apply_patch edits; Copilot shell and file edits; Antigravity shell
and file edits. Cursor cannot block an edit in advance; the commit check covers that.
"""

import json
import re
import shlex
import sys

from afc.config import current_session
from afc.hooks.common import GuardInputError, read_event, string_values
from afc.hooks.pretool import decide

TOOLS = ("cursor", "codex", "copilot", "antigravity")
_PATCH_FILE = re.compile(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+?)\s*$", re.MULTILINE)


def _bash(command: str, cwd: str | None) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd or "."}


def _write(path: str, cwd: str | None, content) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}, "cwd": cwd or "."}


def _text(value) -> str:
    """A command that may arrive as a string or as a list of words."""
    if isinstance(value, list):
        return shlex.join(str(part) for part in value)
    if isinstance(value, str):
        return value
    raise GuardInputError("the command is missing")


def _need(value, what: str):
    if not value:
        raise GuardInputError(f"{what} is missing")
    return value


def cursor_events(data: dict) -> list[dict]:
    name = data.get("hook_event_name")
    if name == "beforeShellExecution":
        return [_bash(_text(data.get("command")), data.get("cwd"))]
    if name == "beforeReadFile":
        return [{"tool_name": "Read", "tool_input": {"file_path": _need(data.get("file_path"), "file_path")},
                 "cwd": data.get("cwd") or "."}]
    return []  # MCP calls and the rest are not ours to judge


def codex_events(data: dict) -> list[dict]:
    tool, tool_input, cwd = data.get("tool_name"), data.get("tool_input") or {}, data.get("cwd")
    if tool == "Bash":
        return [_bash(_text(tool_input.get("command")), cwd)]
    if tool == "apply_patch":
        patch = _text(tool_input.get("command"))
        paths = _PATCH_FILE.findall(patch)
        if not paths:
            raise GuardInputError("the patch names no file")
        return [_write(path, cwd, patch) for path in paths]
    return []


def copilot_events(data: dict) -> list[dict]:
    tool, cwd, args = data.get("toolName"), data.get("cwd"), data.get("toolArgs")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {"command": args}
    args = args if isinstance(args, dict) else {}
    if tool in ("bash", "powershell"):
        return [_bash(_text(args.get("command")), cwd)]
    if tool in ("create", "edit"):
        path = _need(args.get("path") or args.get("file_path"), "the file path")
        return [_write(path, cwd, string_values(args))]
    return []


def antigravity_events(data: dict) -> list[dict]:
    call = data.get("toolCall") or {}
    name, args = call.get("name"), call.get("args") or {}
    roots = data.get("workspacePaths") or []
    cwd = args.get("Cwd") or (roots[0] if roots else None)
    if name == "run_command":
        return [_bash(_text(args.get("CommandLine")), cwd)]
    if name in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
        return [_write(_need(args.get("TargetFile"), "TargetFile"), cwd, string_values(args))]
    return []


EVENTS = {"cursor": cursor_events, "codex": codex_events, "copilot": copilot_events,
          "antigravity": antigravity_events}


def reply(tool: str, reason: str | None) -> tuple[str, str, int]:
    """(stdout, stderr, exit code) in the words this tool expects."""
    if tool == "cursor":
        if reason is None:
            return json.dumps({"permission": "allow"}), "", 0
        said = f"Flight Control blocked: {reason}"
        return json.dumps({"permission": "deny", "user_message": said, "agent_message": said}), "", 2
    if tool == "codex":
        return ("", "", 0) if reason is None else ("", f"Flight Control blocked: {reason}", 2)
    if tool == "copilot":
        if reason is None:
            return json.dumps({"permissionDecision": "allow"}), "", 0
        return json.dumps({"permissionDecision": "deny",
                           "permissionDecisionReason": f"Flight Control blocked: {reason}"}), "", 0
    if reason is None:  # antigravity
        return json.dumps({}), "", 0
    return json.dumps({"decision": "deny", "reason": f"Flight Control blocked: {reason}"}), "", 0


def run(tool: str, stdin_text: str, stdout, stderr) -> int:
    try:
        reason = None
        for event in EVENTS[tool](read_event(stdin_text)):
            reason = decide(event, current_session())
            if reason:
                break
    except Exception as exc:  # fail closed on anything unreadable
        reason = f"the guard could not read this {tool} action ({exc})"
    out, err, code = reply(tool, reason)
    if out:
        print(out, file=stdout)
    if err:
        print(err, file=stderr)
    return code


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in TOOLS:
        print(f"Flight Control blocked: unknown tool {name!r} for the hook adapter.", file=sys.stderr)
        sys.exit(2)
    sys.exit(run(name, sys.stdin.read(), sys.stdout, sys.stderr))
