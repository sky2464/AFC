import unittest

from afc.registry import RegistryError
from afc.workspace import PLAN_SUBDIRS, WORKSPACE_DIRS, create_workspace
from tests.helpers import AfcTestCase

PLAN_FILES = sorted(
    [
        "intent.md",
        "decisions.md",
        "master-plan.md",
        "drift-notes.md",
        "architecture.md",
        "process-steps.md",
    ]
)


class WorkspaceTest(AfcTestCase):
    def test_workspace_layout(self):
        ws = create_workspace(self.home, "kong-gateway-lab")
        self.assertEqual(ws, self.home / "projects" / "kong-gateway-lab")
        self.assertEqual(sorted(p.name for p in ws.iterdir()), sorted([*WORKSPACE_DIRS, "mcp.json"]))
        self.assertTrue((ws / "plan" / "intent.md").exists())
        self.assertTrue((ws / "drafts").is_dir())

    def test_plan_templates_are_copied_with_headings(self):
        ws = create_workspace(self.home, "kong-gateway-lab")
        plan = ws / "plan"
        files = sorted(p.name for p in plan.iterdir() if p.is_file())
        self.assertEqual(files, PLAN_FILES)
        self.assertEqual(sorted(p.name for p in plan.iterdir() if p.is_dir()), sorted(PLAN_SUBDIRS))
        self.assertEqual(PLAN_SUBDIRS, ("specs", "archive"))
        self.assertFalse((plan / "progress.md").exists())
        self.assertFalse((ws / "spec.md").exists())
        for name in PLAN_FILES:
            with self.subTest(file=name):
                self.assertTrue((plan / name).read_text().startswith("# "))

    def test_workspace_does_not_overwrite(self):
        ws = create_workspace(self.home, "kong-gateway-lab")
        intent = ws / "plan" / "intent.md"
        intent.write_text("# Intent\n\nkeep me\n")
        create_workspace(self.home, "kong-gateway-lab")
        self.assertEqual(intent.read_text(), "# Intent\n\nkeep me\n")

    def test_invalid_name_rejected_before_touching_disk(self):
        with self.assertRaises(RegistryError):
            create_workspace(self.home, "../x")
        self.assertFalse((self.home / "x").exists())
        self.assertFalse((self.home / "projects").exists())


if __name__ == "__main__":
    unittest.main()
