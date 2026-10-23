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

_KEYWORD = r"(?:password|passwd|secret|api[_-]?key|token|client[_-]?secret)"
# Quoted value; the keyword may sit inside a longer identifier (AWS_SECRET_ACCESS_KEY).
_GENERIC = re.compile(
    _KEYWORD + r"[A-Za-z0-9_-]*"
    r"\s*[:=]\s*" r"[\"']([^\"'\s]{12,})[\"']",
    re.IGNORECASE,
)
_IDENT = r"^[ \t]*(?:export[ \t]+)?[A-Za-z0-9_.-]*" + _KEYWORD + r"[A-Za-z0-9_.-]*"
_VALUE = r"([^\s\"'#()\[\]{}]{12,})[ \t]*(?:#.*)?$"
# Unquoted .env-style line anywhere: NAME=value with no spaces.
_ENV_LINE = re.compile(_IDENT + r"=" + _VALUE, re.IGNORECASE | re.MULTILINE)
# Unquoted line in a config file: NAME = value or name: value.
_CONFIG_LINE = re.compile(_IDENT + r"[ \t]*[:=][ \t]*" + _VALUE, re.IGNORECASE | re.MULTILINE)
CONFIG_SUFFIXES = (".env", ".yaml", ".yml", ".ini", ".cfg")


def _is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def is_config_file(filename: str) -> bool:
    """True for .env-style and YAML/INI/CFG files, where values are often unquoted."""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name.startswith(".env") or name.endswith(CONFIG_SUFFIXES)


def find_secrets(text: str, filename: str | None = None) -> list[str]:
    """Names of the secret patterns found in text, in a fixed order, each once.

    `filename`, when given, lets config files match unquoted `name: value` lines too.
    """
    found = [name for name, pattern in _PATTERNS if pattern.search(text)]
    line = _CONFIG_LINE if filename and is_config_file(filename) else _ENV_LINE
    values = [m.group(1) for m in _GENERIC.finditer(text)]
    values += [m.group(1) for m in line.finditer(text)]
    if any(not _is_placeholder(v) for v in values):
        found.append("generic-assignment")
    return found
