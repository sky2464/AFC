"""Tests for `sh bin/afc home`: the workspace folder this copy uses, and where it came from."""

import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from afc.config import set_maintain
from tests.helpers import AfcTestCase, run_cli


class HomeCommandTest(AfcTestCase):
    def show(self, **env):
        with mock.patch.dict(os.environ, env, clear=True):
            code, out = run_cli(["home"])
        self.assertEqual(code, 0, out)
        return out

    def test_reports_the_env_source(self):
        self.assertEqual(self.show(AFC_HOME=str(self.home), AFC_HOME_SOURCE="env"),
                         {"home": str(self.home.resolve()), "source": "env"})

    def test_reports_the_file_source(self):
        target = self.tmp / "test-home"
        self.assertEqual(self.show(AFC_HOME=str(target), AFC_HOME_SOURCE="file"),
                         {"home": str(target.resolve()), "source": "file"})

    def test_reports_the_default_home(self):
        self.assertEqual(self.show(HOME=str(self.tmp), AFC_HOME_SOURCE="default"),
                         {"home": str((self.tmp / ".A-FC").resolve()), "source": "default"})

    def test_without_the_launcher_source_comes_from_AFC_HOME(self):
        self.assertEqual(self.show(AFC_HOME=str(self.home))["source"], "env")
        self.assertEqual(self.show(HOME=str(self.tmp))["source"], "default")


class HomeSetClearTest(AfcTestCase):
    """home set|clear write .afc-home in the Flight Control folder (faked here by self.tmp)."""

    def setUp(self):
        super().setUp()
        patch = mock.patch("afc.cli_home.afc_root", return_value=self.tmp)
        patch.start()
        self.addCleanup(patch.stop)
        self.file = self.tmp / ".afc-home"

    def test_set_writes_the_home_file(self):
        set_maintain(self.home, True)
        target = self.tmp / "test-home"
        code, out = run_cli(["home", "set", str(target)])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.file.read_text(), f"{target}\n")
        self.assertEqual(out["home_file"], str(target))

    def test_clear_removes_the_home_file(self):
        set_maintain(self.home, True)
        self.file.write_text("/somewhere\n")
        code, out = run_cli(["home", "clear"])
        self.assertEqual(code, 0, out)
        self.assertFalse(self.file.exists())

    def test_clear_with_no_file_is_fine(self):
        set_maintain(self.home, True)
        code, out = run_cli(["home", "clear"])
        self.assertEqual(code, 0, out)
        self.assertFalse(out["cleared"])

    def test_set_needs_maintenance_mode(self):
        code, out = run_cli(["home", "set", str(self.tmp / "x")])
        self.assertEqual(code, 1)
        self.assertIn("maintenance mode", out["error"])
        self.assertFalse(self.file.exists())

    def test_clear_needs_maintenance_mode(self):
        self.file.write_text("/somewhere\n")
        code, out = run_cli(["home", "clear"])
        self.assertEqual(code, 1)
        self.assertTrue(self.file.exists())

    def test_set_refuses_a_relative_path(self):
        set_maintain(self.home, True)
        code, out = run_cli(["home", "set", "relative/home"])
        self.assertEqual(code, 1)
        self.assertIn("full folder path", out["error"])
        self.assertFalse(self.file.exists())

    def test_plain_home_still_shows_the_home(self):
        code, out = run_cli(["home"])
        self.assertEqual(code, 0)
        self.assertIn("source", out)


class HomeFileIgnoredTest(unittest.TestCase):
    def test_afc_home_is_git_ignored(self):
        root = Path(__file__).resolve().parent.parent
        done = subprocess.run(["git", "check-ignore", "-q", ".afc-home"], cwd=root)
        self.assertEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
