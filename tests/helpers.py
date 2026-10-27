"""Shared test helpers: isolated AFC_HOME per test."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class AfcTestCase(unittest.TestCase):
    """Each test gets its own AFC_HOME and scratch dir; both are removed after."""

    def setUp(self):
        self._saved_home_env = os.environ.get("AFC_HOME")
        self.home = Path(tempfile.mkdtemp(prefix="afc-home-"))
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-tmp-"))
        os.environ["AFC_HOME"] = str(self.home)
        patcher = mock.patch("afc.update.start_refresh", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
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
