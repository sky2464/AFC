"""Tests for the SessionStart welcome hook."""

import io
import json
from unittest import mock

from afc.hooks import session_start
from afc.hooks.session_start import BANNER, INTRO, build_output, main
from afc.registry import Project, Registry, save_registry
from tests.helpers import AfcTestCase


class SessionStartTest(AfcTestCase):
    def _ctx(self, out):
        return out["hookSpecificOutput"]["additionalContext"]

    def test_first_run(self):
        out = build_output(self.home)
        self.assertEqual(
            out["systemMessage"],
            f"{INTRO}\nType 1 to start a new project, 2 to bring in one already on this computer, "
            "or just say hi.")
        self.assertTrue(out["systemMessage"].startswith("✈️  Flight Control"))
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")
        ctx = self._ctx(out)
        self.assertIn("Active project: none — first run.", ctx)
        self.assertIn("The welcome asked: 1 = start a new project, "
                      "2 = bring in one already on this computer.", ctx)

    def test_projects_but_none_active(self):
        reg = Registry()
        reg.add(Project(name="kong-gateway-lab", code_path="/c", workspace_path="/w"))
        save_registry(self.home, reg)
        out = build_output(self.home)
        self.assertEqual(
            out["systemMessage"],
            f"{INTRO}\nWelcome back. Type 1 to pick one of your projects, 2 to start a new project, "
            "or just say hi.")
        ctx = self._ctx(out)
        self.assertIn("Active project: none. Other projects: kong-gateway-lab.", ctx)
        self.assertIn("1 = pick one of your projects, 2 = start a new project.", ctx)

    def test_returning_user(self):
        reg = Registry()
        reg.add(Project(name="kong-gateway-lab", code_path="/c/kong", workspace_path="/w/kong",
                        profile="api", last_slice="add rate limit"))
        reg.add(Project(name="other-app", code_path="/c/o", workspace_path="/w/o"))
        reg.set_active("kong-gateway-lab")
        save_registry(self.home, reg)
        ctx = self._ctx(build_output(self.home))
        self.assertIn(
            "Active project: kong-gateway-lab (api), code: /c/kong, workspace: /w/kong, "
            "last slice: add rate limit. Other projects: other-app.", ctx)
        self.assertIn("afc-start skill", ctx)
        self.assertIn("1 = continue kong-gateway-lab, 2 = something else.", ctx)
        self.assertTrue(build_output(self.home)["systemMessage"].endswith(
            "Welcome back. Type 1 to continue kong-gateway-lab (last: add rate limit), "
            "2 for something else, or just say hi."))

    def test_long_last_slice_is_shortened(self):
        reg = Registry()
        reg.add(Project(name="app", code_path="/c", workspace_path="/w",
                        last_slice="add a health endpoint that reports database and cache status"))
        reg.set_active("app")
        save_registry(self.home, reg)
        line = build_output(self.home)["systemMessage"].splitlines()[1]
        self.assertIn("(last: add a health endpoint that reports data…)", line)

    def test_no_last_slice_and_no_others(self):
        reg = Registry()
        reg.add(Project(name="solo-app", code_path="/c", workspace_path="/w"))
        reg.set_active("solo-app")
        save_registry(self.home, reg)
        ctx = self._ctx(build_output(self.home))
        self.assertIn("last slice: none. Other projects: none.", ctx)

    def test_welcome_with_corrupt_registry(self):
        (self.home / "projects.json").write_text("{")
        out = build_output(self.home)
        self.assertEqual(out["systemMessage"], BANNER)
        self.assertIn("Registry unreadable", self._ctx(out))
        self.assertIn("offer to repair it", self._ctx(out))

    def test_unexpected_error_still_valid(self):
        with mock.patch.object(session_start, "load_registry", side_effect=RuntimeError("boom")):
            out = build_output(self.home)
        self.assertEqual(out["systemMessage"], BANNER)
        self.assertIn("Registry unreadable: boom", self._ctx(out))

    def test_main_always_zero(self):
        buf = io.StringIO()
        self.assertEqual(main(buf), 0)
        self.assertTrue(json.loads(buf.getvalue())["systemMessage"].startswith(INTRO))
        (self.home / "projects.json").write_text("{")
        buf = io.StringIO()
        self.assertEqual(main(buf), 0)
        self.assertIn("Registry unreadable", json.loads(buf.getvalue())["hookSpecificOutput"]["additionalContext"])
