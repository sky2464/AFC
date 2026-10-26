"""An empty architecture.md from before the Key files column still counts as empty."""

import shutil
import tempfile
import unittest
from pathlib import Path

from afc.cli_health import _architecture_problems, architecture_is_bare
from afc.config import afc_root
from afc.registry import Project

OLD_HEADER = "| Name | Responsibility | Talks to |\n|---|---|---|"
NEW_HEADER = "| Name | Responsibility | Key files | Talks to |\n|---|---|---|---|"


class ArchitectureBareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="afc-arch-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.template = (afc_root() / "templates" / "workspace" / "plan" / "architecture.md").read_text()
        self.old = self.template.replace(NEW_HEADER, OLD_HEADER, 1)
        self.assertNotEqual(self.old, self.template)
        self.ws = self.tmp / "plan"
        self.ws.mkdir()
        self.app = self.tmp / "app"
        self.app.mkdir()

    def _project(self, last_slice: str) -> Project:
        return Project(name="demo", code_path=str(self.app), workspace_path=str(self.tmp), last_slice=last_slice)

    def test_the_current_empty_template_is_bare(self):
        path = self.ws / "architecture.md"
        path.write_text(self.template)
        self.assertTrue(architecture_is_bare(path))

    def test_the_old_three_column_template_is_still_bare(self):
        path = self.ws / "architecture.md"
        path.write_text(self.old)
        self.assertTrue(architecture_is_bare(path))
        problems = _architecture_problems(self._project("1 hello"))
        self.assertEqual([item["kind"] for item in problems], ["architecture_empty"])

    def test_a_filled_old_table_is_not_an_empty_template(self):
        path = self.ws / "architecture.md"
        path.write_text(self.old.replace(OLD_HEADER, OLD_HEADER + "\n| app | serves pages | browser |", 1))
        self.assertFalse(architecture_is_bare(path))
        self.assertEqual(_architecture_problems(self._project("1 hello")), [])


if __name__ == "__main__":
    unittest.main()
