"""Keep-awake command: awake on|off|status.

Registered into the main parser by afc.cli through register(). A spec build turns it on before its
first helper and off when it returns, so the Mac does not sleep mid-build. It wraps macOS
`caffeinate -i` with a four-hour limit, so a forgotten build does not keep the Mac up forever.
"""

import argparse
import json
import os
import signal
import subprocess
import sys

from afc.config import afc_home

NAMES = ("awake",)
LIMIT_SECONDS = 4 * 60 * 60
NOT_MACOS = {"awake": False, "reason": "not macOS"}


def register(sub) -> None:
    p = sub.add_parser("awake", help="keep the Mac awake while building, or show it")
    p.add_argument("state", choices=["on", "off", "status"])
    p.set_defaults(handler=cmd_awake)


def is_macos() -> bool:
    return sys.platform == "darwin"


def _state_file():
    return afc_home() / "awake.json"


def _running_pid() -> int | None:
    try:
        pid = int(json.loads(_state_file().read_text())["pid"])
        os.kill(pid, 0)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return pid


def _on_battery() -> bool:
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True,
                             timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "Battery Power" in out


def cmd_awake(args: argparse.Namespace) -> dict:
    if not is_macos():
        return dict(NOT_MACOS)
    pid = _running_pid()
    if args.state == "on" and pid is None:
        proc = subprocess.Popen(["caffeinate", "-i", "-t", str(LIMIT_SECONDS)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        pid = proc.pid
        _state_file().parent.mkdir(parents=True, exist_ok=True)
        _state_file().write_text(json.dumps({"pid": pid}))
    elif args.state == "off":
        if pid is not None:
            os.kill(pid, signal.SIGTERM)
            try:  # reap it when this process started it, so it doesn't linger as a zombie
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
        _state_file().unlink(missing_ok=True)
        pid = None
    result: dict = {"awake": pid is not None, "on_battery": _on_battery()}
    if pid is not None:
        result["pid"] = pid
    return result
