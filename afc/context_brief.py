"""Compact per-project context for fewer reads per slice (FC-022 / FC-023)."""

import re
from pathlib import Path

from afc import plan
from afc.role_agents import load_routing, routing_summary

BRIEF_NAME = "afc-brief.md"
INTENT = "intent.md"
ARCH = "architecture.md"
MAX_BYTES = 4096


def brief_path(workspace: Path) -> Path:
    return Path(workspace) / "resources" / BRIEF_NAME


def _first_paragraph(path: Path, limit: int = 400) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            text = re.sub(r"\s+", " ", line)
            return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
    return ""


def refresh(workspace: Path, profile: str = "personal") -> dict:
    """Rewrite resources/afc-brief.md from plan files and routing. Never raises."""
    ws = Path(workspace)
    plan_dir = ws / "plan"
    intent = _first_paragraph(plan_dir / INTENT)
    arch = _first_paragraph(plan_dir / ARCH)
    try:
        spec_line = plan.now_line(ws) or ""
    except Exception:
        spec_line = ""
    routing = load_routing(ws)
    models = routing_summary(routing, profile)["roles"]
    lines = [
        "# Project brief (Flight Control)",
        "",
        "Read this once at the start of a slice instead of re-reading intent, architecture and routing.",
        "",
        "## Intent",
        intent or "(not written yet)",
        "",
        "## Architecture",
        arch or "(not written yet)",
        "",
        "## Active work",
        spec_line or "(no spec in Now — run sh bin/afc plan)",
        "",
        "## Role models",
        ", ".join(f"{role}={models[role]}" for role in models),
        "",
        "After deliver, run `sh bin/afc context refresh` if intent or architecture changed.",
    ]
    text = "\n".join(lines) + "\n"
    if len(text.encode("utf-8")) > MAX_BYTES:
        text = text.encode("utf-8")[: MAX_BYTES - 20].decode("utf-8", errors="ignore").rstrip() + "\n…\n"
    dest = brief_path(ws)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return {"brief": str(dest), "bytes": len(text.encode("utf-8"))}
