"""Tests for the CI status line and the workflow file (FC-019 slice 5)."""

import json
import subprocess
import unittest
from pathlib import Path

from afc import ci_status

ROOT = Path(__file__).resolve().parent.parent


def fake(payload, code=0):
    def run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, code, json.dumps(payload), "")
    return run


def has_gh(_):
    return "/usr/bin/gh"


class CiStatusTest(unittest.TestCase):
    def test_a_failed_run_says_fix_it_first(self):
        out = ci_status.last_run(ROOT, fake([{"status": "completed", "conclusion": "failure", "url": "u"}]), has_gh)
        self.assertEqual(out["state"], "failed")
        self.assertTrue(out["fix_first"])
        self.assertIn("failed", out["line"])
        self.assertIn("Fixing it comes first", out["line"])

    def test_a_passed_run(self):
        out = ci_status.last_run(ROOT, fake([{"status": "completed", "conclusion": "success"}]), has_gh)
        self.assertEqual(out["state"], "passed")
        self.assertFalse(out["fix_first"])
        self.assertIn("passed", out["line"])

    def test_no_gh_says_nothing(self):
        def boom(*a, **k):
            raise AssertionError("gh must not run")
        out = ci_status.last_run(ROOT, boom, lambda _: None)
        self.assertEqual(out, {"state": "unknown", "line": "", "fix_first": False})

    def test_not_signed_in_or_no_runs_says_nothing(self):
        self.assertEqual(ci_status.last_run(ROOT, fake([], 1), has_gh)["line"], "")
        self.assertEqual(ci_status.last_run(ROOT, fake([]), has_gh)["line"], "")

    def test_afc_shows_it(self):
        text = (ROOT / ".claude" / "commands" / "afc.md").read_text(encoding="utf-8")
        self.assertIn("sh bin/afc ci", text)


class WorkflowFileTest(unittest.TestCase):
    def test_names_both_triggers_and_the_command(self):
        text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        self.assertRegex(text, r"push:\s*\n\s*branches: \[dev\]")
        self.assertRegex(text, r"pull_request:\s*\n\s*branches: \[main\]")
        self.assertIn("sh bin/afc test", text)
        self.assertIn('"3.12"', text)


if __name__ == "__main__":
    unittest.main()
