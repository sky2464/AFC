"""Project profile and rule-module selection.

Classifies a project from plain interview answers, then picks which security
rule modules load for a slice (profile base set plus what the slice touches).
"""

from dataclasses import dataclass

PROFILES = ("personal", "prototype", "mvp", "work", "enterprise")

# Canonical order; also the file names in rules/.
ALL_MODULES = (
    "secrets",
    "identity",
    "input",
    "api",
    "logging-pii",
    "dependencies",
    "containers-deploy",
    "data",
    "architecture",
    "ai-safety",
)


@dataclass
class Answers:
    purpose: str  # learning | personal | prototype | mvp | work | product
    users: int
    audience: str  # self | internal | external | both
    company: str | None
    sensitive_data: bool


def classify(a: Answers) -> str:
    """Return the profile name for a set of answers. First match wins."""
    if a.company:
        if a.audience in ("external", "both") or a.users > 50 or a.sensitive_data:
            return "enterprise"
        return "work"
    if a.purpose in ("mvp", "product"):
        return "mvp"
    if a.purpose == "prototype":
        return "prototype"
    return "personal"


BASE_MODULES: dict[str, tuple[str, ...]] = {
    "personal": ("secrets", "input", "ai-safety"),
    "prototype": ("secrets", "input", "dependencies", "ai-safety"),
    "mvp": ("secrets", "input", "api", "logging-pii", "dependencies", "architecture", "ai-safety"),
    "work": (
        "secrets",
        "identity",
        "input",
        "api",
        "logging-pii",
        "dependencies",
        "containers-deploy",
        "data",
        "architecture",
        "ai-safety",
    ),
    "enterprise": ALL_MODULES,
}

TOUCH_MAP = {
    "auth": "identity",
    "api": "api",
    "data": "data",
    "deploy": "containers-deploy",
    "logs": "logging-pii",
    "deps": "dependencies",
    "input": "input",
}


def modules_for(profile: str, touches: set[str]) -> list[str]:
    """Base modules for the profile, plus modules for touched areas, in ALL_MODULES order.

    Unknown touches are ignored. An unknown profile raises ValueError.
    """
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    wanted = set(BASE_MODULES[profile])
    wanted.update(TOUCH_MAP[t] for t in touches if t in TOUCH_MAP)
    return [m for m in ALL_MODULES if m in wanted]
