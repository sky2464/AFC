import io
import unittest
from unittest.mock import patch

from afc.hooks import pretool
from afc.hooks.common import Context
from afc.config import afc_root
from afc.registry import Project
from tests.helpers import AfcTestCase, make_event


class PreToolTestCase(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.app = self.tmp / "app"
        self.app.mkdir()
        self.ctx = Context(
            home=self.home,
            root=afc_root(),
            active=Project(name="demo", code_path=str(self.app), workspace_path=str(self.tmp)),
            maintain=False,
        )
        patcher = patch("afc.hooks.pretool.load_context", return_value=self.ctx)
        patcher.start()
        self.addCleanup(patcher.stop)


class TestMain(PreToolTestCase):
    def test_empty_stdin_blocks(self):
        err = io.StringIO()
        self.assertEqual(pretool.main("", err), 2)
        self.assertIn("Flight Control guard error", err.getvalue())

    def test_unknown_tool_allowed(self):
        err = io.StringIO()
        self.assertEqual(pretool.main(make_event("Read", {}, self.tmp), err), 0)
        self.assertEqual(err.getvalue(), "")

    def test_outside_write_blocked_with_prefix(self):
        err = io.StringIO()
        code = pretool.main(
            make_event("Write", {"file_path": "/Users/x/other/a.py"}, self.tmp), err
        )
        self.assertEqual(code, 2)
        self.assertTrue(err.getvalue().startswith("Flight Control blocked:"))
        self.assertIn("/Users/x/other/a.py", err.getvalue())

    def test_inside_write_allowed(self):
        err = io.StringIO()
        code = pretool.main(
            make_event("Write", {"file_path": str(self.app / "a.py")}, self.tmp), err
        )
        self.assertEqual(code, 0)

    def test_internal_error_fails_closed(self):
        def broken(event, ctx):
            raise RuntimeError("boom")

        err = io.StringIO()
        with patch.object(pretool, "RULES", [broken]):
            code = pretool.main(
                make_event("Write", {"file_path": str(self.app / "a.py")}, self.tmp), err
            )
        self.assertEqual(code, 2)
        self.assertIn("Flight Control guard error: boom", err.getvalue())

    def test_stdin_read_error_exits_2(self):
        class BrokenStdin:
            def read(self):
                raise OSError("stdin gone")

        err = io.StringIO()
        with patch("sys.stdin", BrokenStdin()):
            code = pretool.run(err)
        self.assertEqual(code, 2)
        self.assertIn("Flight Control guard error", err.getvalue())

    def test_rules_list_starts_with_path_rule(self):
        from afc.hooks.rules_paths import check_paths

        self.assertEqual(pretool.RULES, [check_paths])


if __name__ == "__main__":
    unittest.main()
