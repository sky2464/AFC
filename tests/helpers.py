"""Shared test helpers: isolated AFC_HOME, hook-event builders, CLI runner."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class AfcTestCase(unittest.TestCase):
    """Gives each test its own AFC_HOME and scratch dir; both are removed after."""

    def setUp(self):
        self._saved_home_env = os.environ.get("AFC_HOME")
        self.home = Path(tempfile.mkdtemp(prefix="afc-home-"))
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-tmp-"))
        os.environ["AFC_HOME"] = str(self.home)

    def tearDown(self):
        if self._saved_home_env is None:
            os.environ.pop("AFC_HOME", None)
        else:
            os.environ["AFC_HOME"] = self._saved_home_env
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.tmp, ignore_errors=True)


def make_event(tool_name: str, tool_input: dict, cwd: Path) -> str:
    """Build the hook stdin JSON for a PreToolUse event."""
    return json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "cwd": str(cwd),
        }
    )


def ev(tool_name: str, tool_input: dict, cwd: Path | None = None) -> dict:
    """Same hook event as make_event, returned as a dict. cwd defaults to /."""
    return json.loads(make_event(tool_name, tool_input, cwd or Path("/")))


def bash(command: str, cwd: Path | None = None) -> dict:
    """Hook event for a Bash tool call running `command`."""
    return ev("Bash", {"command": command}, cwd)


def fixture(name: str) -> str:
    """Contents of tests/fixtures/<name>."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def run_cli(argv: list[str]) -> tuple[int, dict]:
    """Run afc.cli.main(argv) and return (exit code, parsed JSON stdout).

    afc.cli is imported here, not at module load, so this module imports
    before the CLI exists.
    """
    from afc import cli

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cli.main(argv)
    return code, json.loads(buf.getvalue())
