"""Slice checks: run the available security checks, summarise in one line, write a report.

The built-in secret scan always runs. Optional tools that are not installed are
reported as missing, never silently skipped.
"""

import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from afc.secrets import find_secrets

MAX_SCAN_BYTES = 1024 * 1024
TOOL_TIMEOUT = 600
ICONS = {"pass": "✅", "warn": "⚠️", "fail": "❌"}


@dataclass
class Check:
    name: str
    status: str  # pass | fail | warn | missing
    detail: str


def _vuln_check(name: str, total: int, high: int) -> Check:
    if total == 0:
        return Check(name, "pass", "0 vulnerable deps")
    return Check(name, "fail", f"{total} vulnerable deps ({high} high)")


def parse_npm_audit(text: str) -> Check:
    """Check from `npm audit --json` output (metadata.vulnerabilities)."""
    try:
        counts = json.loads(text)["metadata"]["vulnerabilities"]
        total = int(counts.get("total", 0))
        high = int(counts.get("high", 0)) + int(counts.get("critical", 0))
    except (ValueError, KeyError, TypeError, AttributeError):
        if "ENOLOCK" in text:
            return Check("npm audit", "warn", "no lockfile, so dependencies were not audited")
        return Check("npm audit", "warn", "npm audit output unreadable")
    return _vuln_check("npm audit", total, high)


def parse_bun_audit(text: str) -> Check:
    """Check from `bun audit --json` output: {package: [advisory with severity, ...]}."""
    try:
        found = json.loads(text)
        total = len(found)
        high = sum(
            1 for advisories in found.values() for a in advisories
            if a.get("severity") in ("high", "critical")
        )
        if not isinstance(found, dict):
            raise TypeError
    except (ValueError, KeyError, TypeError, AttributeError):
        return Check("bun audit", "warn", "bun audit output unreadable")
    return _vuln_check("bun audit", total, high)


def parse_pip_audit(text: str) -> Check:
    """Check from `pip-audit -f json` output. pip-audit gives no severity, so high is 0."""
    try:
        deps = json.loads(text)["dependencies"]
        total = sum(1 for d in deps if d.get("vulns"))
    except (ValueError, KeyError, TypeError, AttributeError):
        return Check("pip-audit", "warn", "pip-audit output unreadable")
    return _vuln_check("pip-audit", total, 0)


def builtin_secret_scan(code_path: Path) -> Check:
    """find_secrets over every tracked text file of at most 1 MB."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z"], cwd=code_path, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return Check("secrets", "warn", "could not list tracked files")
    hits = 0
    for raw in listed.split(b"\0"):
        if not raw:
            continue
        path = code_path / raw.decode("utf-8", "surrogateescape")
        try:
            if not path.is_file() or path.stat().st_size > MAX_SCAN_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data:
            continue
        if find_secrets(data.decode("utf-8", "replace"), path.name):
            hits += 1
    if hits:
        return Check("secrets", "fail", f"secrets in {hits} file(s)")
    return Check("secrets", "pass", "no secrets")


AGENT_FILE_NAMES = {
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules", ".windsurfrules", ".clinerules",
}


def _is_agent_file(path: str) -> bool:
    if path.rsplit("/", 1)[-1] in AGENT_FILE_NAMES:
        return True
    if path == ".github/copilot-instructions.md" or path.endswith("/.github/copilot-instructions.md"):
        return True
    return path.startswith(".cursor/rules/") or "/.cursor/rules/" in path


def agent_files_scan(code_path: Path) -> Check | None:
    """Warn about agent instruction files added or changed since the last commit; None when there are none."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "-z", "--untracked-files=all"],
            cwd=code_path, capture_output=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    entries = out.split(b"\0")
    found: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i].decode("utf-8", "surrogateescape")
        i += 1
        if len(entry) < 4:
            continue
        if entry[0] in "RC":
            i += 1  # the original name follows a rename or copy
        if entry[:2] == " D" or entry[:2] == "D ":
            continue
        if _is_agent_file(entry[3:]):
            found.append(entry[3:])
    if not found:
        return None
    return Check("agent files", "warn", "agent instruction file(s) changed, not followed: " + ", ".join(sorted(found)))


def _run_tool(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TOOL_TIMEOUT)


def _tool(name: str, cmd: list[str], cwd: Path, judge) -> Check:
    if shutil.which(cmd[0]) is None:
        return Check(name, "missing", "")
    try:
        done = _run_tool(cmd, cwd)
    except (OSError, subprocess.TimeoutExpired):
        return Check(name, "warn", f"{name} did not finish")
    return judge(done)


def _judge_gitleaks(done) -> Check:
    if done.returncode == 0:
        return Check("gitleaks", "pass", "gitleaks found no leaks")
    return Check("gitleaks", "fail", "gitleaks found leaks")


def _judge_semgrep(done) -> Check:
    try:
        count = len(json.loads(done.stdout).get("results", []))
    except (ValueError, AttributeError):
        return Check("semgrep", "warn", "semgrep output unreadable")
    if count == 0:
        return Check("semgrep", "pass", "no code findings")
    return Check("semgrep", "warn", f"{count} code finding(s)")


def pip_audit_command(code: Path) -> list[str]:
    """Audit the project's own dependencies, not the active environment."""
    if (code / "requirements.txt").exists():
        return ["pip-audit", "-f", "json", "-r", str(code / "requirements.txt")]
    return ["pip-audit", "-f", "json", str(code)]


def run_checks(code_path: Path) -> list[Check]:
    code = Path(code_path)
    checks = [builtin_secret_scan(code)]
    agent_files = agent_files_scan(code)
    if agent_files:
        checks.append(agent_files)
    checks.append(_tool(
        "gitleaks", ["gitleaks", "detect", "--no-git", "-s", str(code), "--report-format", "json"],
        code, _judge_gitleaks,
    ))
    if (code / "package.json").exists() and ((code / "bun.lock").exists() or (code / "bun.lockb").exists()):
        checks.append(_tool("bun audit", ["bun", "audit", "--json"], code,
                            lambda d: parse_bun_audit(d.stdout)))
    elif (code / "package.json").exists():
        checks.append(_tool("npm audit", ["npm", "audit", "--json"], code,
                            lambda d: parse_npm_audit(d.stdout)))
    if (code / "requirements.txt").exists() or (code / "pyproject.toml").exists():
        checks.append(_tool("pip-audit", pip_audit_command(code), code,
                            lambda d: parse_pip_audit(d.stdout)))
    checks.append(_tool("semgrep", ["semgrep", "--config", "auto", "--json", "--quiet"],
                        code, _judge_semgrep))
    return checks


def summary_line(checks: list[Check]) -> str:
    parts = []
    for c in checks:
        if c.status == "missing":
            parts.append(f"⚪ {c.name} not installed")
        else:
            parts.append(f"{ICONS.get(c.status, '⚠️')} {c.detail}")
    return " · ".join(parts)


def slug(label: str) -> str:
    """Lowercase, non-alphanumerics to '-', trimmed, at most 40 characters."""
    text = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return text[:40].strip("-") or "slice"


def write_report(workspace: Path, checks: list[Check], label: str) -> Path:
    """Write reports/<stamp>-<slug>.md and a .json sidecar with the same stem."""
    now = datetime.now()
    reports = Path(workspace) / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"{now.strftime('%Y-%m-%d-%H%M')}-{slug(label)}.md"
    summary = summary_line(checks)
    lines = [f"# Slice checks: {label}", "", summary, "", "## Checks", ""]
    for c in checks:
        detail = "not installed" if c.status == "missing" else c.detail
        lines.append(f"- **{c.name}** ({c.status}): {detail}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sidecar = {
        "label": label,
        "created": now.isoformat(timespec="seconds"),
        "summary": summary,
        "checks": [asdict(c) for c in checks],
    }
    path.with_suffix(".json").write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    return path
