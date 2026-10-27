"""Which AI tool is running, and which model to suggest (FC-052).

Reads environment variables and home-folder settings. For three options when the user does not
know, also does a timed public look-up and may cache results under ~/.A-FC/model-options/. Never
ships model version IDs in this repo.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from afc.config import afc_home

TOOLS = ("claude", "cursor", "codex", "copilot", "antigravity")

# Public docs only (no API keys). URLs may change; model names are never listed here.
LOOKUP_URLS = {
    "cursor": ("https://cursor.com/docs/models", "https://cursor.com/docs/models-and-pricing"),
    "codex": ("https://developers.openai.com/codex",),
    "copilot": ("https://docs.github.com/en/copilot",),
    "antigravity": ("https://antigravity.google/docs",),
}

LOOKUP_TIMEOUT = 8
# Family words only — never a concrete version ID. Order = preference within the band.
_STRONG = ("fable", "opus", "wonder", "max", "pro", "grok")
_BALANCED = ("sonnet", "terra", "codex", "sol")
_LIGHT = ("composer", "haiku", "flash", "mini", "nano", "luna", "lite")
# Slug IDs and short display names from vendor pages — never a full sentence.
_MODEL_SLUG = re.compile(
    r"\b((?:claude|gpt|gemini|grok|composer|deepseek|glm|kimi|muse)"
    r"[\w.\-]{2,40})\b",
    re.I,
)
_MODEL_DISPLAY = re.compile(
    r"\b((?:Claude|GPT|Gemini|Grok|Composer|DeepSeek|GLM|Kimi|Muse)"
    r"(?:[\s-](?:[A-Z][a-z0-9]+|[A-Z]{2,}|\d+(?:\.\d+)*)){1,5})\b"
)
_BAD_MODEL = re.compile(
    r"\b(and|the|uses|aren|is|for|with|from|on|to|of|or|also|benefits|"
    r"access|apps|plans|billed|context|window|third|party|cursor)\b|[.!?]|,{2}",
    re.I,
)

# First match wins. Unknown when none match.
_TOOL_ENV = (
    ("claude", ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_ENTRYPOINT", "CLAUDECODE")),
    ("cursor", ("CURSOR_AGENT",)),
    ("codex", ("CODEX_HOME", "CODEX_SANDBOX", "CODEX_API_KEY")),
    ("copilot", ("COPILOT_AGENT", "GITHUB_COPILOT", "COPILOT_CLI")),
    ("antigravity", ("ANTIGRAVITY", "GEMINI_CLI", "GEMINI_API_KEY")),
)

def detect_tool(environ: dict[str, str] | None = None) -> str:
    """One of TOOLS, or 'unknown'."""
    env = os.environ if environ is None else environ
    for name, keys in _TOOL_ENV:
        for key in keys:
            value = env.get(key, "").strip()
            if value:
                return name
    return "unknown"


def _cursor_model(home: Path) -> dict:
    path = home / ".cursor" / "cli-config.json"
    if not path.is_file():
        return {"model": None, "file": None, "shown": False, "detail": "not shown"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"model": None, "file": str(path), "shown": False, "detail": "not shown"}
    model = None
    block = data.get("model")
    if isinstance(block, dict):
        model = block.get("modelId") or block.get("displayName")
    if not model:
        selected = data.get("selectedModel")
        if isinstance(selected, dict):
            model = selected.get("modelId")
    if not model or not isinstance(model, str):
        return {"model": None, "file": str(path), "shown": False, "detail": "not shown"}
    return {"model": model, "file": str(path), "shown": True, "detail": model}


def _toml_key(path: Path, key: str) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    pattern = re.compile(rf'^{re.escape(key)}\s*=\s*["\']([^"\']+)["\']\s*(?:#.*)?$')
    for line in text.splitlines():
        m = pattern.match(line.strip())
        if m:
            return m.group(1)
    return None


def _codex_model(home: Path) -> dict:
    path = home / ".codex" / "config.toml"
    if not path.is_file():
        return {"model": None, "file": None, "shown": False, "detail": "not shown"}
    model = _toml_key(path, "model")
    if not model:
        return {"model": None, "file": str(path), "shown": False, "detail": "not shown"}
    return {"model": model, "file": str(path), "shown": True, "detail": model}


def _antigravity_model(home: Path) -> dict:
    """Antigravity / Gemini: look for a plain model key; otherwise not shown."""
    candidates = (
        home / ".gemini" / "settings.json",
        home / ".gemini" / "config" / "config.json",
        home / ".gemini" / "state.json",
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        model = _find_model_string(data)
        if model:
            return {"model": model, "file": str(path), "shown": True, "detail": model}
    return {"model": None, "file": None, "shown": False, "detail": "not shown"}


def _find_model_string(obj, depth: int = 0) -> str | None:
    if depth > 4:
        return None
    if isinstance(obj, dict):
        for key in ("model", "modelId", "selectedModel"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested = value.get("modelId") or value.get("name") or value.get("model")
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()
        for value in obj.values():
            found = _find_model_string(value, depth + 1)
            if found:
                return found
    return None


def shown_model(tool: str | None = None, home: Path | None = None) -> dict:
    """The model the tool's plain settings show, or not shown.

    Returns {tool, model, file, shown, detail}. detail is the model name or "not shown".
    """
    tool = tool or detect_tool()
    base = Path.home() if home is None else Path(home)
    if tool == "cursor":
        found = _cursor_model(base)
    elif tool == "codex":
        found = _codex_model(base)
    elif tool == "antigravity":
        found = _antigravity_model(base)
    elif tool in ("copilot", "claude", "unknown"):
        found = {"model": None, "file": None, "shown": False, "detail": "not shown"}
    else:
        found = {"model": None, "file": None, "shown": False, "detail": "not shown"}
    return {"tool": tool, **found}


def _has_family(name: str, words: tuple[str, ...]) -> bool:
    """True when a family word appears as its own token (not inside gemini/composer)."""
    lower = (name or "").lower()
    for word in words:
        if re.search(rf"(^|[^a-z0-9]){re.escape(word)}([^a-z0-9]|$)", lower):
            return True
    return False


def fit(model: str) -> str:
    """strong, balanced or light from family words in the name (no version pinning)."""
    if _has_family(model, _LIGHT):
        return "light"
    if _has_family(model, _BALANCED):
        return "balanced"
    if _has_family(model, _STRONG):
        return "strong"
    return "balanced"


def need(role: str, routing: dict | None = None, profile: str = "personal") -> str:
    """Job need for a role: strong, balanced or light, from FC-050 routing aliases."""
    from afc.role_agents import resolve_model

    return fit(resolve_model(role, routing, profile=profile))


def local_models(tool: str | None = None, home: Path | None = None) -> list[str]:
    """Distinct model names listed in the tool's plain local settings."""
    tool = tool or detect_tool()
    base = Path.home() if home is None else Path(home)
    found: list[str] = []
    if tool == "cursor":
        path = base / ".cursor" / "cli-config.json"
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            block = data.get("model")
            if isinstance(block, dict):
                for key in ("modelId", "displayName", "displayModelId"):
                    if isinstance(block.get(key), str) and block[key].strip():
                        found.append(block[key].strip())
            selected = data.get("selectedModel")
            if isinstance(selected, dict) and isinstance(selected.get("modelId"), str):
                found.append(selected["modelId"].strip())
            explore = data.get("exploreSubagentModel")
            if isinstance(explore, str) and explore.strip() and explore.strip().lower() != "default":
                found.append(explore.strip())
            params = data.get("modelParameters")
            if isinstance(params, dict):
                found.extend(str(k) for k in params if isinstance(k, str) and k.strip())
    elif tool == "codex":
        shown = _codex_model(base)
        if shown.get("model"):
            found.append(shown["model"])
    elif tool == "antigravity":
        shown = _antigravity_model(base)
        if shown.get("model"):
            found.append(shown["model"])
    # de-dupe, keep order
    out: list[str] = []
    for name in found:
        if name and name not in out:
            out.append(name)
    return out


def _cache_path(tool: str, home: Path | None = None) -> Path:
    root = Path(home) if home is not None else afc_home()
    return root / "model-options" / f"{tool}.json"


def _read_cache(tool: str, home: Path | None = None) -> dict | None:
    path = _cache_path(tool, home)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    models = data.get("models")
    if not isinstance(models, list) or not models:
        return None
    return data


def _write_cache(tool: str, models: list[str], source: str, home: Path | None = None) -> None:
    path = _cache_path(tool, home)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "checked": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": source,
            "models": models,
        }, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def _clean_model_name(raw: str) -> str | None:
    name = " ".join((raw or "").split()).strip(" |`\"'*,;:()[]{}")
    if len(name) < 5 or len(name) > 48:
        return None
    if name.lower() in ("claude", "gpt", "gemini", "grok", "composer", "openai", "anthropic"):
        return None
    if _BAD_MODEL.search(name):
        return None
    # Must include a digit or a known family qualifier word
    lower = name.lower()
    if not re.search(r"\d", name) and not any(
        w in lower for w in ("opus", "sonnet", "haiku", "fable", "flash", "pro", "max",
                             "mini", "nano", "composer", "wonder", "terra", "luna", "argon", "codex")
    ):
        return None
    return name


def _extract_models(text: str) -> list[str]:
    found: list[str] = []
    seen_lower: set[str] = set()
    for match in list(_MODEL_SLUG.findall(text or "")) + list(_MODEL_DISPLAY.findall(text or "")):
        name = _clean_model_name(match)
        if not name:
            continue
        key = name.lower().replace(" ", "-").replace("_", "-")
        if key in seen_lower:
            continue
        seen_lower.add(key)
        found.append(name)
    return found


def lookup_models(tool: str, *, home: Path | None = None, fetch: bool = True) -> dict:
    """Live public look-up of model names for a tool; may use or fill the machine cache.

    Returns {models, source, checked, live, error}. Never invents names.
    """
    if not fetch or os.environ.get("AFC_MODEL_LOOKUP", "").strip().lower() in ("0", "off", "false"):
        cached = _read_cache(tool, home)
        if cached:
            return {
                "models": list(cached["models"]),
                "source": cached.get("source"),
                "checked": cached.get("checked"),
                "live": False,
                "error": "look-up switched off",
            }
        return {"models": [], "source": None, "checked": None, "live": False, "error": "look-up switched off"}

    urls = LOOKUP_URLS.get(tool) or ()
    last_error = "no look-up URL for this tool"
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Flight-Control/afc-model"})
            with urllib.request.urlopen(req, timeout=LOOKUP_TIMEOUT) as resp:
                raw = resp.read(2_000_000).decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = str(exc)
            continue
        models = _extract_models(raw)
        if models:
            _write_cache(tool, models, url, home)
            return {
                "models": models,
                "source": url,
                "checked": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "live": True,
                "error": None,
            }
        last_error = f"no model names found at {url}"

    cached = _read_cache(tool, home)
    if cached:
        return {
            "models": list(cached["models"]),
            "source": cached.get("source"),
            "checked": cached.get("checked"),
            "live": False,
            "error": last_error,
        }
    return {"models": [], "source": None, "checked": None, "live": False, "error": last_error}


def _band_words(want: str) -> tuple[str, ...]:
    if want == "strong":
        return _STRONG
    if want == "light":
        return _LIGHT
    return _BALANCED


def _family_rank(name: str, words: tuple[str, ...]) -> int:
    lower = (name or "").lower()
    for i, word in enumerate(words):
        if re.search(rf"(^|[^a-z0-9]){re.escape(word)}([^a-z0-9]|$)", lower):
            return i
    return len(words)


def _pick(candidates: list[str], want: str, prefer: list[str] | None = None) -> str | None:
    matched = [m for m in candidates if fit(m) == want]
    if not matched:
        return None
    words = _band_words(want)
    # Prefer names that carry an explicit family word over bare defaults (e.g. "GPT-5").
    named = [m for m in matched if _family_rank(m, words) < len(words)]
    if named:
        matched = named
    preferred = {p.lower() for p in (prefer or [])}
    # Prefer a name the tool already lists; then better family rank; then shorter slug.
    return sorted(
        matched,
        key=lambda s: (
            0 if s.lower() in preferred else 1,
            _family_rank(s, words),
            len(s),
            s.lower(),
        ),
    )[0]


def suggest(role: str, routing: dict | None, shown: dict | None = None,
            profile: str = "personal", home: Path | None = None) -> dict | None:
    """One switch suggestion from models the tool already lists, or None."""
    shown = shown or shown_model(home=home)
    tool = shown.get("tool") or detect_tool()
    current = shown.get("model")
    if not current:
        return None
    job = need(role, routing, profile=profile)
    if fit(current) == job:
        return None
    if job == "balanced" and fit(current) != "light":
        return None
    locals_ = local_models(tool, home)
    pick = _pick(locals_, job, prefer=locals_)
    if not pick or pick == current:
        return None
    reasons = {
        "strong": "stronger fit for architecture and planning on your plan",
        "balanced": "a middle path for quality and cost on your plan",
        "light": "lighter use of your plan for everyday work",
    }
    return {"model": pick, "need": job, "reason": reasons[job]}


def three_options(tool: str | None = None, home: Path | None = None, *, fetch: bool = True) -> dict:
    """Exactly three options when possible: premium, best cost, hybrid — from local + look-up."""
    tool = tool or detect_tool()
    local = local_models(tool, home)
    looked = lookup_models(tool, home=home, fetch=fetch)
    candidates: list[str] = []
    for name in local + list(looked.get("models") or []):
        if name and name not in candidates:
            candidates.append(name)

    note_parts = []
    if looked.get("live"):
        note_parts.append(f"names from {looked.get('source')}")
    elif looked.get("checked"):
        note_parts.append(f"look-up failed ({looked.get('error')}); using cache from {looked.get('checked')}")
    elif looked.get("error"):
        note_parts.append(f"look-up failed ({looked.get('error')}); local settings only")

    if not candidates:
        return {
            "tool": tool,
            "options": [],
            "recommended": None,
            "lookup": looked,
            "note": "; ".join(note_parts) or "no models found",
        }

    premium = _pick(candidates, "strong", prefer=local)
    cost = _pick(candidates, "light", prefer=local)
    hybrid = _pick(candidates, "balanced", prefer=local)
    # Fill gaps without inventing names — reuse only if we still lack distinct slots
    leftovers = [m for m in candidates if m not in {premium, cost, hybrid}]
    if premium is None and leftovers:
        premium = leftovers.pop(0)
    if cost is None and leftovers:
        cost = leftovers.pop(0)
    if hybrid is None and leftovers:
        hybrid = leftovers.pop(0)
    if hybrid is None:
        hybrid = premium or cost
    if premium is None:
        premium = hybrid or cost
    if cost is None:
        cost = hybrid or premium

    options = [
        {"kind": "premium", "model": premium,
         "reason": "top tier on this tool's subscription for the hardest work"},
        {"kind": "cost", "model": cost,
         "reason": "best for cost on the same plan for everyday work"},
        {"kind": "hybrid", "model": hybrid,
         "reason": "balance of quality and cost on your plan"},
    ]
    # Drop duplicates that would confuse the user — keep first of each model
    seen: set[str] = set()
    unique = []
    for item in options:
        if item["model"] in seen:
            continue
        seen.add(item["model"])
        unique.append(item)
    recommended = "hybrid" if any(o["kind"] == "hybrid" for o in unique) else unique[0]["kind"]
    return {
        "tool": tool,
        "options": unique,
        "recommended": recommended,
        "lookup": looked,
        "note": "; ".join(note_parts) if note_parts else None,
    }
