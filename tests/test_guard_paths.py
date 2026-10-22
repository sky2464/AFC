import os
import unittest
from pathlib import Path
from unittest.mock import patch

from afc.config import afc_root
from afc.hooks.common import (
    Context,
    GuardInputError,
    UNREADABLE_REASON as UNREADABLE,
    bash_write_targets,
    bash_write_targets_or_none,
    read_event,
    string_values,
    strip_heredoc_bodies,
    target_path,
)
from afc.hooks.rules_paths import check_paths
from afc.registry import Project
from tests.helpers import AfcTestCase, bash, ev

ROOT = afc_root()
POLICY = "can't be changed this way"


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
    def test_unparseable_is_blocked(self):
        reason = check_paths(bash('echo "unclosed > /x'), self.ctx)
        self.assertEqual(reason, UNREADABLE)

    def test_ansi_c_quote_redirect_not_silent(self):
        reason = check_paths(bash("echo $'\\'' > /real"), self.ctx)
        self.assertIsNotNone(reason)

    def test_combined_shell_flag_and_eval_followed(self):
        for cmd in ("bash -lc 'echo x > /x'", "sh -xec 'echo x > /x'", "eval 'echo x > /x'",
                    "eval echo x '>' /x"):
            self.assertIsNotNone(check_paths(bash(cmd), self.ctx), cmd)

    def test_shell_script_extraction(self):
        for cmd in ("bash -c -- 'echo x > /x'", "bash -c -o pipefail 'echo x > /x'"):
            self.assertEqual(bash_write_targets_or_none(cmd), ["/x"], cmd)
        for cmd in ("bash <<< 'echo x > /x'", "echo 'echo x > /x' | bash", "bash script.sh"):
            self.assertIsNone(bash_write_targets_or_none(cmd), cmd)
            self.assertIsNotNone(check_paths(bash(cmd), self.ctx), cmd)
        self.assertEqual(bash_write_targets_or_none("bash -c 'git status'"), [])

    def test_script_files_followed(self):
        d = self.tmp / "scripts"
        d.mkdir()
        (d / "w.sh").write_text("echo x > /x\n")
        (d / "ok.sh").write_text("git status\n")
        (d / "bin.sh").write_bytes(b"\0\xff")
        for cmd in ("bash w.sh", "source w.sh", ". w.sh"):
            self.assertEqual(bash_write_targets_or_none(cmd, str(d)), ["/x"], cmd)
            self.assertIsNotNone(check_paths(bash(cmd, cwd=d), self.ctx), cmd)
        self.assertEqual(bash_write_targets_or_none("bash ok.sh", str(d)), [])
        for cmd in ("bash missing.sh", "bash bin.sh"):
            self.assertIsNone(bash_write_targets_or_none(cmd, str(d)), cmd)
            self.assertIsNotNone(check_paths(bash(cmd, cwd=d), self.ctx), cmd)

    def test_heredoc_with_apostrophes_allowed(self):
        cmd = "cat <<'EOF' >> /tmp/f\ndon't\nEOF"
        self.assertIsNone(check_paths(bash(cmd), self.ctx))

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
        # A symlink in the temp dir that points into the active project is allowed.
        link = self.tmp / "link_in"
        link.symlink_to(self.app)
        self.assertIsNone(
            check_paths(ev("Write", {"file_path": str(link / "x.py")}), self.ctx)
        )

    def test_tmp_symlink_outside_blocked(self):
        # A symlink in the temp dir that points outside every allowed root is blocked.
        link = self.tmp / "link_out"
        link.symlink_to(Path.home() / "afc-probe-outside-link")
        self.assertIn(
            "outside",
            check_paths(ev("Write", {"file_path": str(link / "a.txt")}), self.ctx),
        )

    def test_tmp_write_allowed_without_active_project(self):
        self.assertIsNone(
            check_paths(ev("Write", {"file_path": str(self.tmp / "scratch.txt")}), self.ctx_none)
        )

    def test_no_active_project_message(self):
        probe = Path.home() / "afc-probe-outside" / "a.py"
        self.assertIn(
            "type /afc",
            check_paths(ev("Write", {"file_path": str(probe)}), self.ctx_none),
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

    def test_project_parent_of_afc_root_cannot_write_into_afc(self):
        # An active project whose code_path contains A-FC must not reach into A-FC.
        project = Project(
            name="parent", code_path=str(ROOT.parent), workspace_path=str(self.workspace)
        )
        ctx = Context(home=self.home, root=ROOT, active=project, maintain=False)
        self.assertIn(
            "maintenance mode",
            check_paths(ev("Write", {"file_path": str(ROOT / "CLAUDE.md")}), ctx),
        )

    def test_project_parent_still_allows_siblings(self):
        project = Project(
            name="parent", code_path=str(ROOT.parent), workspace_path=str(self.workspace)
        )
        ctx = Context(home=self.home, root=ROOT, active=project, maintain=False)
        sibling = ROOT.parent / "sibling-project" / "a.py"
        self.assertIsNone(check_paths(ev("Write", {"file_path": str(sibling)}), ctx))

    def test_home_maintain_file_blocked(self):
        self.assertIn(
            POLICY,
            check_paths(ev("Write", {"file_path": str(self.home / "maintain")}), self.ctx),
        )

    def test_home_projects_json_blocked(self):
        self.assertIn(
            POLICY,
            check_paths(ev("Write", {"file_path": str(self.home / "projects.json")}), self.ctx),
        )

    def test_home_projects_md_blocked(self):
        self.assertIn(
            POLICY,
            check_paths(ev("Edit", {"file_path": str(self.home / "projects.md")}), self.ctx),
        )

    def test_claude_settings_blocked(self):
        path = str(Path.home() / ".claude" / "settings.json")
        self.assertIn(POLICY, check_paths(ev("Write", {"file_path": path}), self.ctx))

    def test_claude_settings_local_blocked_even_in_maintain(self):
        path = str(Path.home() / ".claude" / "settings.local.json")
        ctx = Context(home=self.home, root=ROOT, active=self.ctx.active, maintain=True)
        self.assertIn(POLICY, check_paths(ev("Write", {"file_path": path}), ctx))

    def test_afc_claude_settings_blocked_without_maintain(self):
        path = str(ROOT / ".claude" / "settings.json")
        self.assertIn(POLICY, check_paths(ev("Write", {"file_path": path}), self.ctx))

    def test_afc_claude_settings_allowed_with_maintain(self):
        path = str(ROOT / ".claude" / "settings.json")
        ctx = Context(home=self.home, root=ROOT, active=self.ctx.active, maintain=True)
        self.assertIsNone(check_paths(ev("Write", {"file_path": path}), ctx))

    def test_project_plan_file_under_home_allowed(self):
        path = self.home / "projects" / "demo" / "plan" / "intent.md"
        self.assertIsNone(check_paths(ev("Write", {"file_path": str(path)}), self.ctx))

    def test_notebook_path_checked(self):
        self.assertIn(
            "outside",
            check_paths(ev("NotebookEdit", {"notebook_path": "/Users/x/n.ipynb"}), self.ctx),
        )

    def test_write_event_without_path_blocked(self):
        with self.assertRaises(GuardInputError):
            check_paths(ev("Write", {"content": "x"}), self.ctx)

    def test_bash_redirect_outside_blocked(self):
        self.assertIsNotNone(check_paths(bash("echo hi > /Users/x/o.txt"), self.ctx))

    def test_bash_redirect_into_code_allowed(self):
        self.assertIsNone(check_paths(bash(f"echo hi > {self.app}/o.txt"), self.ctx))

    def test_bash_cp_into_code_allowed(self):
        self.assertIsNone(check_paths(bash(f"cp notes.txt {self.app}/"), self.ctx))

    def test_bash_cp_outside_blocked(self):
        self.assertIsNotNone(check_paths(bash("cp notes.txt /Users/x/elsewhere/"), self.ctx))

    def test_bash_write_to_home_control_file_blocked(self):
        command = f"echo x > {self.home / 'projects.json'}"
        self.assertIn(POLICY, check_paths(bash(command), self.ctx))

    def test_bash_without_write_targets_passes(self):
        self.assertIsNone(check_paths(bash("ls -la /Users/x"), self.ctx))

    def test_read_tool_not_checked(self):
        self.assertIsNone(check_paths(ev("Read", {"file_path": "/Users/x/o.txt"}), self.ctx))


class TestBashWriteTargets(unittest.TestCase):
    def test_redirects_and_tee(self):
        self.assertEqual(bash_write_targets("echo a >> /x/a.txt"), ["/x/a.txt"])
        self.assertEqual(bash_write_targets("ls | tee -a /x/b.txt"), ["/x/b.txt"])

    def test_cp_mv_rsync_take_last_argument(self):
        self.assertEqual(bash_write_targets("mv a b /x/dir"), ["/x/dir"])
        self.assertEqual(bash_write_targets("rsync -av src/ /x/dst/"), ["/x/dst"])

    def test_dev_null_and_fd_dup_ignored(self):
        self.assertEqual(bash_write_targets("cmd 2>&1 > /dev/null"), [])

    def test_fd_prefix_is_not_a_tee_argument(self):
        self.assertEqual(bash_write_targets("tee /x/a 2>&1"), ["/x/a"])

    def test_unparseable_gives_none(self):
        self.assertIsNone(bash_write_targets_or_none('echo "unclosed > /x'))
        self.assertEqual(bash_write_targets('echo "unclosed > /x'), [])

    def test_ampersand_greater_than_word_is_file_target(self):
        self.assertEqual(bash_write_targets("echo hi >& /Users/x/o.txt"), ["/Users/x/o.txt"])

    def test_numeric_dup_is_not_a_file(self):
        self.assertEqual(bash_write_targets("echo hi >&2"), [])

    def test_cp_dash_t_destination(self):
        self.assertEqual(
            bash_write_targets("cp -t /Users/x/elsewhere src.txt"), ["/Users/x/elsewhere"]
        )

    def test_cp_target_directory_equals(self):
        self.assertEqual(bash_write_targets("cp --target-directory=/x src"), ["/x"])

    def test_hash_is_not_a_comment(self):
        self.assertEqual(bash_write_targets("echo x#y > /Users/x/o"), ["/Users/x/o"])

    def test_cd_changes_base_for_later_targets(self):
        self.assertEqual(
            bash_write_targets("cd /Users/x && echo hi > o.txt"), ["/Users/x/o.txt"]
        )

    def test_sudo_wrapper_before_tee(self):
        self.assertEqual(bash_write_targets("sudo tee /x"), ["/x"])

    def test_assignment_prefix_before_cp(self):
        self.assertEqual(bash_write_targets("FOO=1 cp a /x"), ["/x"])

    def test_shell_dash_c_is_parsed_recursively(self):
        self.assertEqual(bash_write_targets("bash -c 'echo x > /x'"), ["/x"])

    def test_tilde_is_expanded(self):
        expected = str(Path.home().resolve() / "afc-probe" / "o")
        self.assertEqual(bash_write_targets("echo hi > ~/afc-probe/o"), [expected])

    def test_environment_variable_is_expanded(self):
        with patch.dict(os.environ, {"AFC_TEST_DIR": "/Users/x"}):
            self.assertEqual(bash_write_targets("echo hi > $AFC_TEST_DIR/o"), ["/Users/x/o"])

    def test_unexpanded_variable_is_skipped(self):
        self.assertEqual(bash_write_targets("echo hi > $AFC_UNSET_VAR_XYZ/o"), [])

    def test_backtick_target_is_skipped(self):
        self.assertEqual(bash_write_targets("echo hi > `pwd`/o"), [])


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


class TestHeredocBodies(unittest.TestCase):
    def test_reviewer_example_only_tmp_target(self):
        cmd = "cat <<'EOF' >> /x/f\na <b>/c\nEOF"
        self.assertEqual(bash_write_targets(cmd), ["/x/f"])

    def test_quoted_and_unquoted_tags(self):
        for op in ('<<"T"', "<<T", "<< T", "<<\\T"):
            cmd = f"cat {op} > /x/f\nx > /y/z\nT"
            self.assertEqual(bash_write_targets(cmd), ["/x/f"], op)

    def test_dash_heredoc_allows_tab_terminator(self):
        cmd = "cat <<-T > /x/f\n\tx > /y/z\n\tT\necho > /x/after"
        self.assertEqual(bash_write_targets(cmd), ["/x/f", "/x/after"])

    def test_two_heredocs(self):
        cmd = "cat <<A > /x/1\n> /y/a\nA\ncat <<'B' > /x/2\n> /y/b\nB"
        self.assertEqual(bash_write_targets(cmd), ["/x/1", "/x/2"])

    def test_two_heredocs_one_line(self):
        cmd = "cat <<A <<B > /x/1\n> /y/a\nA\n> /y/b\nB\necho > /x/2"
        self.assertEqual(bash_write_targets(cmd), ["/x/1", "/x/2"])

    def test_redirect_after_terminator_detected(self):
        cmd = "cat <<EOF\nbody\nEOF\necho hi > /x/after"
        self.assertEqual(bash_write_targets(cmd), ["/x/after"])

    def test_unterminated_drops_rest(self):
        cmd = "cat <<EOF > /x/f\n> /y/z"
        self.assertEqual(bash_write_targets(cmd), ["/x/f"])

    def test_single_quoted_operator_not_heredoc(self):
        cmd = "echo '<<EOF' > /x\necho hi > /real"
        self.assertEqual(bash_write_targets(cmd), ["/x", "/real"])

    def test_double_quoted_operator_not_heredoc(self):
        cmd = 'echo "<<EOF"\necho hi > /real'
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_comment_operator_not_heredoc(self):
        cmd = "# <<EOF\necho hi > /real"
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_escaped_operator_not_heredoc(self):
        cmd = "echo a\\<<EOF\necho > /real"
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_arithmetic_shift_not_heredoc(self):
        cmd = "x=$((1<<EOF))\necho > /real"
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_single_quote_spanning_lines_not_heredoc(self):
        cmd = "echo 'a\n<<EOF'\necho > /real"
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_double_quote_spanning_lines_not_heredoc(self):
        cmd = 'echo "a\n<<EOF"\necho > /real'
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_arithmetic_command_not_heredoc(self):
        cmd = "((x=1<<EOF))\necho > /real"
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_old_arithmetic_not_heredoc(self):
        cmd = "echo $[1<<EOF]\necho > /real"
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_parameter_expansion_not_heredoc(self):
        cmd = "echo ${x:-<<EOF}\necho > /real"
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_quoted_tag_line_in_body_then_real_target(self):
        cmd = 'cat <<EOF\n"EOF"\nEOF\necho > /real'
        self.assertEqual(bash_write_targets(cmd), ["/real"])

    def test_hash_inside_word_is_real_heredoc(self):
        cmd = "echo a#<<EOF\nbody > /x\nEOF"
        self.assertEqual(bash_write_targets(cmd), [])

    def test_unclosed_construct_strips_nothing(self):
        cmd = "cat <<EOF\nbody > /x\nEOF\necho 'open"
        self.assertEqual(strip_heredoc_bodies(cmd), cmd)

    def test_ansi_c_escaped_quote_hides_no_target(self):
        cmd = "echo $'\\'' '<<EOF' #'\necho hi > real.txt"
        self.assertIn("/private/tmp/real.txt", bash_write_targets(cmd, "/private/tmp"))

    def test_here_string_unaffected(self):
        cmd = "cat <<< word > /x/f\necho > /x/g"
        self.assertEqual(bash_write_targets(cmd), ["/x/f", "/x/g"])


if __name__ == "__main__":
    unittest.main()
