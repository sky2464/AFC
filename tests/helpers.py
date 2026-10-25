"""Shared test helpers: isolated AFC_HOME, hook-event builders, CLI runner."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class AfcTestCase(unittest.TestCase):
    """Gives each test its own AFC_HOME and scratch dir; both are removed after.

    Looking for a newer Flight Control release finds nothing by default, so no test reaches the
    real remote; a test that needs the real lookup against a test remote sets offline_updates
    to False (see RemoteCase).
    """

    offline_updates = True

    def setUp(self):
        self._saved_home_env = os.environ.get("AFC_HOME")
        self.home = Path(tempfile.mkdtemp(prefix="afc-home-"))
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-tmp-"))
        os.environ["AFC_HOME"] = str(self.home)
        if self.offline_updates:
            patcher = mock.patch("afc.update.remote_newest", return_value=None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        if self._saved_home_env is None:
            os.environ.pop("AFC_HOME", None)
        else:
            os.environ["AFC_HOME"] = self._saved_home_env
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.tmp, ignore_errors=True)


def git(cwd, *args, **extra_env):
    """Run git in a test repo with no user or system config and a fixed identity."""
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, **extra_env)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main", *args],
        cwd=cwd, check=True, capture_output=True, env=env,
    )


class RemoteCase(AfcTestCase):
    """A test remote on main with one release (v0.01a), and a clone of it as the Flight Control copy."""

    offline_updates = False

    def setUp(self):
        super().setUp()
        self.remote = self.tmp / "remote"
        self.remote.mkdir()
        git(self.remote, "init", "-q")
        (self.remote / "VERSION").write_text("v0.01a\n")
        git(self.remote, "add", "VERSION")
        git(self.remote, "commit", "-qm", "one")
        git(self.remote, "tag", "v0.01a")
        self.copy = self.tmp / "copy"
        git(self.tmp, "clone", "-q", str(self.remote), str(self.copy))

    def tag(self, *names):
        for name in names:
            git(self.remote, "tag", name)

    def commit(self, text, date=None):
        (self.remote / "VERSION").write_text(text + "\n")
        when = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date} if date else {}
        git(self.remote, "commit", "-qam", text, **when)

    def write_state(self, **data):
        from afc import update

        (self.home / update.STATE).write_text(json.dumps(data), encoding="utf-8")

    def go_offline(self):
        git(self.copy, "remote", "set-url", "origin", str(self.tmp / "gone"))

    def check(self, now=1_000_000.0):
        from afc import update

        return update.check(self.copy, self.home, now=now)


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
