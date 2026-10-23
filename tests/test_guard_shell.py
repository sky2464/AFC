"""Shell-parsing hardening: option clusters, escaped comments, line continuations, variables."""

from afc.hooks.common import Context, bash_write_targets_or_none
from afc.hooks.rules_git import check_git
from afc.hooks.rules_paths import check_paths
from afc.registry import Project
from tests.helpers import AfcTestCase, bash


class ShellCase(AfcTestCase):
    def setUp(self):
        super().setUp()
        app, ws = self.tmp / "app", self.tmp / "ws"
        app.mkdir()
        ws.mkdir()
        project = Project(name="demo", code_path=str(app), workspace_path=str(ws))
        self.ctx = Context(home=self.home, root=self.tmp / "afc", active=project, maintain=False)

    def blocked_both(self, path_cmd: str, git_cmd: str):
        self.assertIsNotNone(check_paths(bash(path_cmd), self.ctx), path_cmd)
        self.assertIsNotNone(check_git(bash(git_cmd), self.ctx), git_cmd)


class TestOptionClusters(ShellCase):
    def test_env_cluster_with_split_string(self):  # item 1
        self.assertEqual(bash_write_targets_or_none("env -iS 'tee /zz/z'"), ["/zz/z"])
        self.assertEqual(bash_write_targets_or_none("env -iS'tee /zz/z'"), ["/zz/z"])
        self.assertEqual(bash_write_targets_or_none("env -iu X tee /zz/z"), ["/zz/z"])
        self.blocked_both("env -iS 'tee /zz/z'", "env -iS 'git reset --hard'")
        self.assertIsNone(check_git(bash("env -iS 'git status'"), self.ctx))

    def test_sudo_cluster_value_letters(self):  # item 2
        for cmd in ("sudo -iu root tee /zz/q", "sudo -u root tee /zz/q",
                    "sudo -uroot tee /zz/q", "sudo -i -g wheel tee /zz/q"):
            self.assertEqual(bash_write_targets_or_none(cmd), ["/zz/q"], cmd)
        self.blocked_both("sudo -iu root tee /zz/q", "sudo -iu root git reset --hard")
        self.assertIsNone(check_git(bash("sudo -iu root git status"), self.ctx))


class TestEscapesAndContinuations(ShellCase):
    def test_escaped_space_before_hash_is_not_comment(self):  # item 3
        self.assertEqual(bash_write_targets_or_none("echo a\\ #; tee /zz/w"), ["/zz/w"])
        self.blocked_both("echo a\\ #; tee /zz/w", "echo a\\ #; git reset --hard")
        self.assertEqual(bash_write_targets_or_none("echo a # ; tee /zz/w"), [])

    def test_line_continuation_joined(self):  # item 4
        self.assertEqual(bash_write_targets_or_none("echo hi >\\\n/zz/real3"), ["/zz/real3"])
        self.assertEqual(bash_write_targets_or_none("echo hi \\\n> /zz/real3"), ["/zz/real3"])
        self.blocked_both("echo hi >\\\n/zz/real3", "git reset \\\n--hard")
        self.assertEqual(bash_write_targets_or_none("echo 'a\\\nb' > /x"), ["/x"])


class TestChainVariables(ShellCase):
    def test_assigned_variable_expanded(self):  # item 5
        scripts = self.tmp / "s"
        scripts.mkdir()
        (scripts / "x.sh").write_text("git status\n")
        (scripts / "bad.sh").write_text("git reset --hard\n")
        self.assertIsNone(check_git(bash(f"S={scripts}; bash $S/x.sh"), self.ctx))
        self.assertIsNone(check_paths(bash(f"S={scripts}; bash ${{S}}/x.sh"), self.ctx))
        self.assertIsNotNone(check_git(bash(f"S={scripts}; bash $S/bad.sh"), self.ctx))
        self.assertEqual(bash_write_targets_or_none("D=/zz; E=$D/q; echo > $E"), ["/zz/q"])
        self.assertIsNotNone(check_paths(bash("D=/zz; echo > $D/q"), self.ctx))

    def test_unknown_variable_still_blocks_script(self):
        self.assertIsNotNone(check_git(bash("bash $AFC_UNSET_XYZ/x.sh"), self.ctx))
        self.assertIsNotNone(check_git(bash("S=`pwd`; bash $S/x.sh"), self.ctx))
