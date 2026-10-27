"""FC-052 model suggestions read tool settings from the user's home, not ~/.A-FC/."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from afc.tool_model import local_models, role_switch_suggest


class ToolModelHomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-tool-model-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.user_home = self.tmp / "user"
        self.afc_workspace = self.tmp / "afc-ws"
        self.user_home.mkdir()
        self.afc_workspace.mkdir()
        cursor_dir = self.user_home / ".cursor"
        cursor_dir.mkdir()
        (cursor_dir / "cli-config.json").write_text(
            json.dumps(
                {
                    "model": {"modelId": "composer-2.5-fast"},
                    "modelParameters": {
                        "composer-2.5-fast": {},
                        "claude-opus-5-5-medium": {},
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_local_models_uses_user_home_when_home_is_none(self):
        with mock.patch("pathlib.Path.home", return_value=self.user_home):
            names = local_models("cursor", home=None)
        self.assertIn("claude-opus-5-5-medium", names)

    def test_local_models_does_not_read_afc_workspace_as_tool_home(self):
        names = local_models("cursor", home=self.afc_workspace)
        self.assertEqual(names, [])

    @mock.patch("afc.tool_model.lookup_models", return_value={"models": []})
    def test_role_switch_suggest_ignores_afc_workspace_for_locals(self, _lookup):
        shown = {"tool": "cursor", "model": "composer-2.5-fast", "shown": True}
        with mock.patch("pathlib.Path.home", return_value=self.user_home):
            wrong = role_switch_suggest("architect", {}, shown=shown, home=self.afc_workspace)
            right = role_switch_suggest("architect", {}, shown=shown)
        self.assertIsNone(wrong)
        self.assertIsNotNone(right)
        self.assertEqual(right["model"], "claude-opus-5-5-medium")


if __name__ == "__main__":
    unittest.main()
