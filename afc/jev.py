"""Optional TypeSafe Jev adapter (FC-024). Off by default; shadow mode logs only.

Uses stdlib urllib only. No network in tests — inject ``opener`` or leave key unset for no-op.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Callable

API_URL = "https://api.typesafe.ai/v1/systemone"
ENV_KEY = "TYPESAFE_API_KEY"
DEFAULT_TIMEOUT = 8.0


def evaluate(
    state: str,
    questions: dict,
    *,
    model: str = "jev-latest",
    api_key: str | None = None,
    opener: Callable | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict | None:
    """Call System One when a key is set; otherwise None (no-op)."""
    key = api_key if api_key is not None else os.environ.get(ENV_KEY)
    if not key or not str(key).strip():
        return None
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None
