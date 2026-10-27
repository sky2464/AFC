"""Tests for the rebuildable project index (MP-5: specs and archive are searchable)."""

from afc.index import rebuild_project_index, search
from afc.registry import Project, Registry, save_registry
from afc.workspace import create_workspace
from tests.helpers import AfcTestCase


class IndexSpecSearchTests(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.reg = Registry()
        self.ws = create_workspace(self.home, "kong-gateway-lab")
        code = self.tmp / "kong-gateway-lab"
        code.mkdir()
        self.reg.add(
            Project(name="kong-gateway-lab", code_path=str(code), workspace_path=str(self.ws))
        )
        self.reg.set_active("kong-gateway-lab")
        save_registry(self.home, self.reg)

    def test_specs_and_archived_specs_searchable(self):
        for folder, name, word in (
            ("specs", "S-001-x.md", "quokka"),
            ("archive", "S-000-y.md", "wombat"),
        ):
            (self.ws / "plan" / folder).mkdir(exist_ok=True)
            (self.ws / "plan" / folder / name).write_text(
                f"# Spec\n{word} lives here\n", encoding="utf-8"
            )
        db = rebuild_project_index(self.ws, "kong-gateway-lab")
        self.assertEqual(
            [h["path"] for h in search(db, "quokka")],
            ["plan/specs/S-001-x.md"],
        )
        self.assertEqual(
            [h["path"] for h in search(db, "wombat")],
            ["plan/archive/S-000-y.md"],
        )
