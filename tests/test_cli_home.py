"""Tests for `sh bin/afc home`: the workspace folder this copy uses, and where it came from."""

import os
import unittest
from unittest import mock

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


if __name__ == "__main__":
    unittest.main()
