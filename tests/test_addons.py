"""Tests for the allowed add-on list and `afc addons`, with a fake claude on PATH."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from afc import addons
from tests.helpers import AfcTestCase, run_cli
from tests.test_cli import CliTestCase

ALLOWED = ["superpowers@claude-plugins-official"]
PLUGINS = [
    {"id": "superpowers@claude-plugins-official", "enabled": True},
    {"id": "agent-recall@synced", "enabled": True},
    {"id": "off-already@synced", "enabled": False},
]


def put_fake_claude(case, stdout, code=0):
    """Put a `claude` script on PATH (for this test only) that prints stdout."""
    bin_dir = case.tmp / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    out = case.tmp / "out.txt"
    out.write_text(stdout)
    script = bin_dir / "claude"
    script.write_text(f'#!/bin/sh\ncat "{out}"\nexit {code}\n')
    script.chmod(0o755)
    patcher = patch.dict(os.environ, {"PATH": str(bin_dir) + os.pathsep + "/usr/bin:/bin"})
    patcher.start()
    case.addCleanup(patcher.stop)


class AddonsModuleTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "root"
        self.root.mkdir()
        (self.root / "afc-addons.json").write_text(json.dumps({"allowed": ALLOWED}))

    def test_repo_list_allows_superpowers(self):
        real = Path(__file__).resolve().parent.parent
        self.assertEqual(addons.allowed(real), ALLOWED)

    def test_enabled_and_not_allowed_is_blocked(self):
        put_fake_claude(self, json.dumps(PLUGINS))
        self.assertEqual(addons.blocked(self.root), (["agent-recall@synced"], None))

    def test_missing_claude_gives_a_plain_note(self):
        with patch("shutil.which", return_value=None):
            ids, note = addons.blocked(self.root)
        self.assertEqual(ids, [])
        self.assertIn("isn't on the PATH", note)

    def test_bad_json_gives_a_plain_note(self):
        put_fake_claude(self, "not json")
        ids, note = addons.blocked(self.root)
        self.assertEqual(ids, [])
        self.assertIn("couldn't be understood", note)

    def test_missing_list_file_allows_nothing(self):
        (self.root / "afc-addons.json").unlink()
        self.assertEqual(addons.allowed(self.root), [])


class AddonsCommandTest(CliTestCase):
    def setUp(self):
        super().setUp()
        (self.root / "afc-addons.json").write_text(json.dumps({"allowed": ALLOWED}))

    def test_reports_allowed_and_blocked(self):
        with patch("afc.addons.reported", return_value=(PLUGINS, None)):
            rc, out = run_cli(["addons"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(out, {"allowed": ALLOWED, "blocked": ["agent-recall@synced"], "unknown_state": False})

    def test_unknown_state_when_claude_is_missing(self):
        with patch("afc.addons.reported", return_value=([], "Claude Code isn't on the PATH.")):
            rc, out = run_cli(["addons"])
        self.assertEqual(rc, 0, out)
        self.assertTrue(out["unknown_state"])
        self.assertEqual(out["blocked"], [])
        self.assertIn("PATH", out["note"])
