"""Secret detection shared by the write guard, slice scan and commit check.

Pattern strings are written so this source file never matches itself.
"""

import re

PLACEHOLDER_MARKERS = (
    "example", "your", "xxx", "changeme", "placeholder", "dummy",
    "<", "${", "process.env", "os.environ", "redacted",
)

_PATTERNS = (
    ("aws-access-key", re.compile("AKIA" + "[0-9A-Z]{16}")),
    ("private-key", re.compile("-----BEGIN (RSA |EC |OPENSSH |DSA )?" + "PRIVATE KEY-----")),
    ("github-token", re.compile("gh[pousr]_" + "[A-Za-z0-9]{36,}")),
    ("slack-token", re.compile("xox[abprs]-" + "[A-Za-z0-9-]{10,}")),
)

_GENERIC = re.compile(
    r"(password|passwd|secret|api[_-]?key|token|client[_-]?secret)"
    r"\s*[:=]\s*" r"[\"']([^\"'\s]{12,})[\"']",
    re.IGNORECASE,
)


def _is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def find_secrets(text: str) -> list[str]:
    """Names of the secret patterns found in text, in a fixed order, each once."""
    found = [name for name, pattern in _PATTERNS if pattern.search(text)]
    if any(not _is_placeholder(m.group(2)) for m in _GENERIC.finditer(text)):
        found.append("generic-assignment")
    return found
