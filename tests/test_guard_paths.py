import unittest
from pathlib import Path

from afc.config import afc_root
from afc.hooks.common import (
    Context,
    GuardInputError,
    bash_write_targets,
    read_event,
    string_values,
    target_path,
)
from afc.hooks.rules_paths import check_paths
from afc.registry import Project
from tests.helpers import AfcTestCase, bash, ev

ROOT = afc_root()


class GuardPathTestCase(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.app = self.tmp / "app"
        self.app.mkdir()
        self.workspace = self.tmp / "ws"
        self.workspace.mkdir()
        project = Project(
            name="demo",
            code_path=str(self.app),
            workspace_path=str(self.workspace),
        )
        self.ctx = Context(home=self.home, root=ROOT, active=project, maintain=False)
        self.ctx_none = Context(home=self.home, root=ROOT, active=None, maintain=False)


class TestCheckPaths(GuardPathTestCase):
    def test_write_inside_code_path_allowed(self):
        self.assertIsNone(
            check_paths(ev("Write", {"file_path": str(self.app / "src/x.py")}), self.ctx)
        )

    def test_write_outside_blocked(self):
        self.assertIn(
            "outside",
            check_paths(ev("Write", {"file_path": "/Users/x/other/a.py"}), self.ctx),
        )

    def test_relative_path_resolved_against_cwd(self):
        self.assertIsNone(
            check_paths(ev("Edit", {"file_path": "src/x.py"}, cwd=self.app), self.ctx)
        )

    def test_escape_with_dotdot_blocked(self):
        # The project sits under the temp dir, where ../ would still be an allowed root,
        # so use a project under home that is not an allowed root.
        code = Path.home() / "afc-probe-app" / "code"
        project = Project(name="demo", code_path=str(code), workspace_path=str(self.workspace))
        ctx = Context(home=self.home, root=ROOT, active=project, maintain=False)
        self.assertIsNotNone(
            check_paths(ev("Write", {"file_path": "../evil.py"}, cwd=code), ctx)
        )

    def test_tmp_symlink_allowed(self):
        self.assertIsNone(
            check_paths(ev("Write", {"file_path": "/tmp/scratch.txt"}), self.ctx)
        )

    def test_no_active_project_message(self):
        probe = Path.home() / "afc-probe-outside" / "a.py"
        self.assertIn(
            "type /afc",
            check_paths(ev("Write", {"file_path": str(probe)}), self.ctx_none),
        )

    def test_tmp_write_allowed_without_active_project(self):
        self.assertIsNone(
            check_paths(ev("Write", {"file_path": str(self.tmp / "scratch.txt")}), self.ctx_none)
        )

    def test_afc_root_without_maintain_and_no_project_says_maintenance(self):
        self.assertIn(
            "maintenance mode",
            check_paths(ev("Write", {"file_path": str(ROOT / "CLAUDE.md")}), self.ctx_none),
        )

    def test_afc_root_needs_maintain(self):
        self.assertIn(
            "maintenance mode",
            check_paths(ev("Write", {"file_path": str(ROOT / "CLAUDE.md")}), self.ctx),
        )

    def test_afc_root_allowed_in_maintain_mode(self):
        ctx = Context(home=self.home, root=ROOT, active=self.ctx.active, maintain=True)
        self.assertIsNone(
            check_paths(ev("Write", {"file_path": str(ROOT / "CLAUDE.md")}), ctx)
        )

    def test_write_event_without_path_blocked(self):
        with self.assertRaises(GuardInputError):
            check_paths(ev("Write", {"content": "x"}), self.ctx)

    def test_notebook_path_checked(self):
        self.assertIn(
            "outside",
            check_paths(ev("NotebookEdit", {"notebook_path": "/Users/x/n.ipynb"}), self.ctx),
        )

    def test_bash_redirect_outside_blocked(self):
        self.assertIsNotNone(
            check_paths(bash("echo hi > /Users/x/o.txt"), self.ctx)
        )

    def test_bash_redirect_into_code_allowed(self):
        self.assertIsNone(
            check_paths(bash(f"echo hi > {self.app}/o.txt"), self.ctx)
        )

    def test_bash_cp_into_code_allowed(self):
        self.assertIsNone(
            check_paths(bash(f"cp notes.txt {self.app}/"), self.ctx)
        )

    def test_bash_cp_outside_blocked(self):
        self.assertIsNotNone(
            check_paths(bash("cp notes.txt /Users/x/elsewhere/"), self.ctx)
        )

    def test_bash_without_write_targets_passes(self):
        self.assertIsNone(check_paths(bash("ls -la /Users/x"), self.ctx))

    def test_read_tool_not_checked(self):
        self.assertIsNone(
            check_paths(ev("Read", {"file_path": "/Users/x/o.txt"}), self.ctx)
        )


class TestBashWriteTargets(unittest.TestCase):
    def test_redirects_and_tee(self):
        self.assertEqual(bash_write_targets("echo a >> /x/a.txt"), ["/x/a.txt"])
        self.assertEqual(bash_write_targets("ls | tee -a /x/b.txt"), ["/x/b.txt"])

    def test_cp_mv_rsync_take_last_argument(self):
        self.assertEqual(bash_write_targets("mv a b /x/dir"), ["/x/dir"])
        self.assertEqual(bash_write_targets("rsync -av src/ /x/dst/"), ["/x/dst/"])

    def test_dev_null_and_fd_dup_ignored(self):
        self.assertEqual(bash_write_targets("cmd 2>&1 > /dev/null"), [])

    def test_unparseable_returns_empty(self):
        self.assertEqual(bash_write_targets('echo "unclosed > /x'), [])


class TestHelpers(unittest.TestCase):
    def test_read_event_rejects_empty_and_non_object(self):
        for text in ("", "   ", "not json", "[1, 2]"):
            with self.subTest(text=text):
                with self.assertRaises(GuardInputError):
                    read_event(text)

    def test_read_event_returns_dict(self):
        self.assertEqual(read_event('{"tool_name": "Read"}'), {"tool_name": "Read"})

    def test_string_values_collects_nested_strings(self):
        obj = {"a": "x", "b": ["y", {"c": "z"}], "n": 3}
        self.assertEqual(sorted(string_values(obj)), ["x", "y", "z"])

    def test_target_path_prefers_file_path_and_resolves_cwd(self):
        event = ev("Write", {"file_path": "rel/a.py"}, cwd=Path("/base"))
        self.assertEqual(target_path(event), Path("/base/rel/a.py").resolve())

    def test_target_path_none_without_path(self):
        self.assertIsNone(target_path(ev("Write", {"content": "x"})))


class TestLoadContext(AfcTestCase):
    def test_corrupt_registry_means_no_active(self):
        from afc.hooks.common import load_context

        (self.home / "projects.json").write_text("{not json", encoding="utf-8")
        ctx = load_context()
        self.assertIsNone(ctx.active)
        self.assertEqual(ctx.home, self.home.resolve())
        self.assertFalse(ctx.maintain)


if __name__ == "__main__":
    unittest.main()
