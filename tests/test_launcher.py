"""Tests for bin/afc: finding a usable Python, and plain messages when there is none."""

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import AfcTestCase

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "bin" / "afc"
SH = shutil.which("sh")
TOOLS = ("cat", "uname", "dirname")

OLD_PYTHON = """#!/bin/sh
case "$2" in
  *print*) echo 3.9.1 ;;
  *) exit 1 ;;
esac
"""
PY_LAUNCHER = f"""#!/bin/sh
shift
exec "{sys.executable}" "$@"
"""


@unittest.skipUnless(SH, "needs a POSIX shell")
class LauncherTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for tool in TOOLS:
            (self.bin / tool).symlink_to(shutil.which(tool))

    def script(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o755)

    def real_python(self, name):
        (self.bin / name).symlink_to(sys.executable)

    def run_afc(self, *args, stdin=""):
        env = {"PATH": str(self.bin), "AFC_HOME": str(self.home), "HOME": str(self.tmp)}
        return subprocess.run([SH, str(LAUNCHER), *args], input=stdin, capture_output=True,
                              text=True, env=env, timeout=60)

    # -- a usable Python exists

    def test_runs_the_command_line_with_python3(self):
        self.real_python("python3")
        done = self.run_afc("status")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), {"active": None, "projects": []})

    def test_skips_an_old_python3_for_a_newer_versioned_one(self):
        self.script("python3", OLD_PYTHON)
        self.real_python("python3.13")
        done = self.run_afc("status")
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_uses_the_windows_py_launcher(self):
        self.script("py", PY_LAUNCHER)
        done = self.run_afc("status")
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_runs_the_hooks(self):
        self.real_python("python3")
        start = self.run_afc("hook", "session_start")
        self.assertEqual(start.returncode, 0, start.stderr)
        self.assertIn("first run", json.loads(start.stdout)["hookSpecificOutput"]["additionalContext"])
        guard = self.run_afc("hook", "pretool", stdin=json.dumps({"tool_name": "Read"}))
        self.assertEqual(guard.returncode, 0, guard.stderr)

    # -- no usable Python

    def test_no_python_welcome_is_one_plain_line(self):
        out = json.loads(self.run_afc("hook", "session_start").stdout)
        self.assertEqual(
            out["systemMessage"],
            "✈️  Flight Control needs Python 3.10 or newer, and this computer doesn't have it yet. "
            "Say hi and I'll help you set it up.")
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("ask one question: may you install it now?", ctx)
        # No installer on this PATH, so the user is pointed to one they run themselves.
        self.assertTrue("python.org" in ctx or "package manager" in ctx, ctx)

    def test_too_old_python_is_named(self):
        self.script("python3", OLD_PYTHON)
        out = json.loads(self.run_afc("hook", "session_start").stdout)
        self.assertIn("This computer has Python 3.9.1, which is too old.", out["systemMessage"])

    def test_no_python_blocks_file_changes(self):
        done = self.run_afc("hook", "pretool", stdin=json.dumps({"tool_name": "Write"}))
        self.assertEqual(done.returncode, 2)
        self.assertTrue(done.stderr.startswith("Flight Control blocked:"))

    def test_no_python_asks_before_every_command(self):
        for event in ('{"tool_name": "Bash"}', '{"tool_name":"Bash"}'):
            done = self.run_afc("hook", "pretool", stdin=event)
            self.assertEqual(done.returncode, 0)
            out = json.loads(done.stdout)["hookSpecificOutput"]
            self.assertEqual(out["permissionDecision"], "ask")

    def test_no_python_command_line_gives_a_plain_error(self):
        done = self.run_afc("status")
        self.assertEqual(done.returncode, 1)
        self.assertIn("needs Python 3.10 or newer", json.loads(done.stdout)["error"])


class LauncherFileTest(unittest.TestCase):
    def test_hooks_go_through_the_launcher(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
        commands = [h["command"] for groups in settings["hooks"].values()
                    for group in groups for h in group["hooks"]]
        self.assertEqual(len(commands), 2)
        for command in commands:
            self.assertTrue(command.startswith('sh "${CLAUDE_PROJECT_DIR}/bin/afc" hook '), command)

    def test_launcher_keeps_unix_line_endings(self):
        self.assertNotIn(b"\r\n", LAUNCHER.read_bytes())
        self.assertIn("bin/afc text eol=lf", (ROOT / ".gitattributes").read_text())

    @unittest.skipIf(os.name == "nt", "file modes")
    def test_launcher_is_executable(self):
        self.assertTrue(os.access(LAUNCHER, os.X_OK))


@unittest.skipUnless(SH, "needs a POSIX shell")
class LauncherHomeFileTest(AfcTestCase):
    """bin/afc reads .afc-home from its own folder when AFC_HOME isn't set."""

    def setUp(self):
        super().setUp()
        # A copy of the launcher with its own .afc-home; the afc package is shared by symlink.
        self.copy = self.tmp / "copy"
        (self.copy / "bin").mkdir(parents=True)
        shutil.copy(LAUNCHER, self.copy / "bin" / "afc")
        (self.copy / "afc").symlink_to(ROOT / "afc")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "python3").symlink_to(sys.executable)
        for tool in TOOLS:
            (self.bin / tool).symlink_to(shutil.which(tool))

    def write_home_file(self, text):
        (self.copy / ".afc-home").write_text(text)

    def run_afc(self, *args, env=None, stdin=""):
        base = {"PATH": str(self.bin), "HOME": str(self.tmp), "PYTHONDONTWRITEBYTECODE": "1"}
        return subprocess.run([SH, str(self.copy / "bin" / "afc"), *args], input=stdin,
                              capture_output=True, text=True, env={**base, **(env or {})},
                              timeout=60)

    def show_home(self, **env):
        done = self.run_afc("home", env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_home_file_sets_the_workspace(self):
        target = self.tmp / "test-home"
        self.write_home_file(f"{target}\n")
        self.assertEqual(self.show_home(), {"home": str(target.resolve()), "source": "file"})

    def test_AFC_HOME_wins_over_the_file(self):
        self.write_home_file(str(self.tmp / "test-home") + "\n")
        self.assertEqual(self.show_home(AFC_HOME=str(self.home)),
                         {"home": str(self.home.resolve()), "source": "env"})

    def test_no_file_and_no_AFC_HOME_means_the_default_home(self):
        self.assertEqual(self.show_home(),
                         {"home": str((self.tmp / ".A-FC").resolve()), "source": "default"})

    def test_relative_path_in_the_file_is_a_plain_error(self):
        self.write_home_file("relative/home\n")
        done = self.run_afc("home")
        self.assertEqual(done.returncode, 1)
        self.assertIn(".afc-home", json.loads(done.stdout)["error"])

    def test_empty_file_is_a_plain_error(self):
        self.write_home_file("")
        done = self.run_afc("home")
        self.assertEqual(done.returncode, 1)
        self.assertIn(".afc-home", json.loads(done.stdout)["error"])

    def test_bad_file_closes_the_guard(self):
        self.write_home_file("relative/home\n")
        done = self.run_afc("hook", "pretool", stdin=json.dumps({"tool_name": "Write"}))
        self.assertEqual(done.returncode, 2)
        self.assertTrue(done.stderr.startswith("Flight Control blocked:"), done.stderr)

    def test_bad_file_asks_before_every_command(self):
        self.write_home_file("relative/home\n")
        done = self.run_afc("hook", "pretool", stdin='{"tool_name": "Bash"}')
        self.assertEqual(done.returncode, 0)
        out = json.loads(done.stdout)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "ask")

    def test_bad_file_is_named_in_the_welcome(self):
        self.write_home_file("relative/home\n")
        done = self.run_afc("hook", "session_start")
        self.assertEqual(done.returncode, 0)
        self.assertIn(".afc-home", json.loads(done.stdout)["systemMessage"])
