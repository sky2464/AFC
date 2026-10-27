"""Maintenance mode with no session ID follows the copy's branch (FC-051 slice 4)."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from afc import cli, config


class BranchMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-mb-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        env = mock.patch.dict(os.environ, {"AFC_HOME": str(self.tmp)})
        env.start()
        self.addCleanup(env.stop)
        for name in ("CLAUDE_CODE_SESSION_ID", "AFC_SESSION"):
            os.environ.pop(name, None)
        self.branch = "feature/x"
        for target, value in (("afc.update._branch", lambda root: self.branch),):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return code, json.loads(out.getvalue())

    def test_on_and_off_without_a_session_id(self):
        self.assertEqual(self.run_cli("maintain")[1], {"maintain": False, "scope": "off"})
        code, result = self.run_cli("maintain", "on")
        self.assertEqual((code, result), (0, {"maintain": True, "scope": "branch"}))
        self.assertEqual(self.run_cli("maintain", "status")[1]["scope"], "branch")
        self.assertEqual(self.run_cli("maintain", "off")[1], {"maintain": False, "scope": "off"})

    def test_it_is_per_branch(self):
        self.run_cli("maintain", "on")
        self.branch = "other"
        self.assertEqual(self.run_cli("maintain")[1]["scope"], "off")

    def test_never_on_for_main(self):
        self.branch = "main"
        code, result = self.run_cli("maintain", "on")
        self.assertEqual(code, 1)
        self.assertIn("error", result)
        self.assertEqual(self.run_cli("maintain")[1]["scope"], "off")

    def test_detached_head_cannot_turn_it_on(self):
        self.branch = ""
        code, result = self.run_cli("maintain", "on")
        self.assertEqual(code, 1)
        self.assertIn("branch", result["error"])

    def test_a_session_id_ignores_the_branch_switch(self):
        self.run_cli("maintain", "on")
        self.assertEqual(config.maintain_scope(config.afc_home(), "sess1"), "off")
        config.set_maintain(config.afc_home(), True, "sess1")
        self.assertEqual(config.maintain_scope(config.afc_home(), "sess1"), "session")
        self.assertEqual(config.maintain_scope(config.afc_home(), None), "branch")


if __name__ == "__main__":
    unittest.main()
