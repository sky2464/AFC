import os
import unittest
from pathlib import Path

from afc.config import afc_home, afc_root, maintain_enabled, set_maintain
from tests.helpers import AfcTestCase


class ConfigTest(AfcTestCase):
    def test_home_from_env(self):
        self.assertEqual(afc_home(), self.home.resolve())

    def test_home_default(self):
        del os.environ["AFC_HOME"]
        self.assertEqual(afc_home(), (Path.home() / ".A-FC").resolve())

    def test_root_contains_claude_md_dir(self):
        self.assertTrue((afc_root() / "afc" / "config.py").exists())

    def test_maintain_toggle(self):
        self.assertFalse(maintain_enabled(self.home))
        set_maintain(self.home, True)
        self.assertTrue(maintain_enabled(self.home))
        set_maintain(self.home, False)
        self.assertFalse(maintain_enabled(self.home))


if __name__ == "__main__":
    unittest.main()
