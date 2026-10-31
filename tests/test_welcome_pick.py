"""FC-056: before the user picks a project, the welcome and context line hold its name only."""

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from afc import cli
from afc.context_brief import brief_path
from afc.hooks.session_start import build_output
from afc.registry import Project, Registry, save_registry


class WelcomePickTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-pick-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.app = self.tmp / "app"
        self.ws = self.home / "projects" / "demo"
        self.app.mkdir()
        self.ws.mkdir(parents=True)
        self.brief = brief_path(self.ws)
        self.brief.parent.mkdir(parents=True, exist_ok=True)
        self.brief.write_text("brief")
        reg = Registry()
        reg.add(Project(name="demo", code_path=str(self.app), workspace_path=str(self.ws),
                        last_slice="login page shows the form"))
        reg.add(Project(name="other", code_path=str(self.tmp / "o"), workspace_path=str(self.tmp / "ow")))
        reg.set_active("demo")
        save_registry(self.home, reg)
        for name in ("afc.hooks.session_start._update_offer", "afc.hooks.session_start._health_line"):
            patcher = mock.patch(name, return_value=None if "offer" in name else "")
            patcher.start()
            self.addCleanup(patcher.stop)
        for name in ("afc.hooks.session_start._addons_line", "afc.hooks.session_start._connectors_line"):
            patcher = mock.patch(name, return_value="")
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_welcome_and_context_name_the_project_only(self):
        out = build_output(self.home)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("demo", out["systemMessage"])
        self.assertIn("demo", context)
        self.assertIn("other", context)
        for detail in (str(self.app), str(self.ws), "login page", str(self.brief)):
            self.assertNotIn(detail, context)
            self.assertNotIn(detail, out["systemMessage"])

    def test_status_after_the_pick_has_the_details(self):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"AFC_HOME": str(self.home)}), contextlib.redirect_stdout(buf):
            self.assertEqual(cli.main(["status"]), 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["code_path"], str(self.app))
        self.assertEqual(out["last_slice"], "login page shows the form")
        self.assertEqual(out["brief"], str(self.brief))

    def test_context_waits_for_the_pick_before_status_or_health(self):
        with mock.patch("afc.hooks.session_start._health_line",
                        return_value=(" Health check: 1 leftover folder permission. "
                                      "Once the user has answered the welcome's question, "
                                      "say this in one plain line, once this session.")):
            context = build_output(self.home)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("do not run status, plan or read project files", context)
        self.assertIn("name the active project only", context)
        self.assertIn("Once the user has answered the welcome's question", context)
        self.assertNotIn("After the question, say this", context)


if __name__ == "__main__":
    unittest.main()
