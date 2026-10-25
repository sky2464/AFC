"""Git that changes the A-FC folder needs maintenance mode; git that only reads never does."""

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from afc.hooks.common import Context
from afc.hooks.pretool import RULES
from afc.hooks.rules_maintenance import changes_git, check_own_copy
from afc.registry import Project
from tests.helpers import AfcTestCase, bash

ROOT = Path(__file__).resolve().parent.parent


class OwnCopyGuardTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.app = self.tmp / "app"
        self.app.mkdir()
        demo = Project(name="demo", code_path=str(self.app),
                       workspace_path=str(self.home / "projects" / "demo"))
        self.off = Context(home=self.home, root=ROOT, active=demo, maintain=False, projects=(demo,))
        self.on = Context(home=self.home, root=ROOT, active=demo, maintain=True, projects=(demo,))

    def blocked(self, command: str, cwd: Path = ROOT) -> str:
        reason = check_own_copy(bash(command, cwd=cwd), self.off)
        self.assertIsNotNone(reason, command)
        return reason

    def allowed(self, command: str, cwd: Path = ROOT, ctx: Context | None = None):
        self.assertIsNone(check_own_copy(bash(command, cwd=cwd), ctx or self.off), command)

    def test_changing_git_in_the_a_fc_folder_needs_maintenance_mode(self):
        for command in ("git merge --ff-only v1.2", "git pull", "git switch dev", "git checkout v1.2",
                        "git cherry-pick abc", "git revert abc", "git stash", "git apply x.patch",
                        "git am x.mbox", "git tag v9", "git commit -m x", "git reset HEAD~1"):
            self.assertIn("needs maintenance mode", self.blocked(command), command)

    def test_the_same_commands_run_with_maintenance_mode_on(self):
        for command in ("git merge --ff-only v1.2", "git checkout v1.2", "git tag v9", "git status"):
            self.allowed(command, ctx=self.on)

    def test_reading_git_works_in_either_mode(self):
        for command in ("git status", "git log --oneline", "git diff HEAD", "git show HEAD",
                        "git describe --tags", "git rev-parse HEAD", "git ls-remote origin",
                        "git ls-files", "git blame afc/cli.py", "git fetch", "git fetch origin",
                        "git tag", "git tag --list", "git tag -l 'v*'", "git branch", "git branch -a",
                        "git branch -r", "git branch --list", "git branch -vv", "git stash list",
                        "git stash show", "git remote", "git remote -v", "git config --get user.name",
                        "git -c core.pager=cat log"):
            self.allowed(command)
            self.allowed(command, ctx=self.on)

    def test_changing_variants_of_listing_commands_are_blocked(self):
        for command in ("git tag v1", "git tag -d v1", "git tag -a v1 -m x", "git branch new",
                        "git branch -D old", "git branch -m old new", "git stash pop", "git stash drop",
                        "git remote add x u", "git remote remove origin", "git config user.name x",
                        "git fetch origin main:main", "git fetch --tags", "git worktree add ../x"):
            self.blocked(command)

    def test_unknown_subcommands_count_as_changing(self):
        self.assertTrue(changes_git("frobnicate", []))
        self.blocked("git frobnicate")

    def test_locations_are_followed(self):
        self.blocked(f"git -C {ROOT} tag v1", cwd=self.tmp)
        self.blocked(f"git --git-dir={ROOT}/.git tag v1", cwd=self.tmp)
        self.blocked(f"git --git-dir {ROOT}/.git --work-tree {ROOT} switch dev", cwd=self.tmp)
        self.blocked(f"cd {ROOT} && git merge x", cwd=self.tmp)
        self.blocked(f"git -C {self.tmp} -C {ROOT} pull", cwd=self.tmp)
        self.blocked("git pull", cwd=ROOT / "afc")
        self.blocked(f"sh -c 'cd {ROOT} && git pull'", cwd=self.tmp)

    def test_git_elsewhere_is_not_affected(self):
        self.allowed("git commit -m x", cwd=self.app)
        self.allowed(f"git -C {self.app} merge x", cwd=ROOT)
        self.allowed(f"git --git-dir {self.app}/.git tag v1", cwd=ROOT)
        self.allowed("git pull", cwd=self.tmp)

    def test_non_git_and_non_bash_are_ignored(self):
        self.allowed("ls -la && echo git merge")
        self.assertIsNone(check_own_copy({"tool_name": "Write", "tool_input": {}}, self.off))
        self.allowed('echo "unclosed')

    def test_rule_is_registered(self):
        self.assertIn(check_own_copy, RULES)


class OwnCopyHeadTest(AfcTestCase):
    """Real repo as the A-FC folder: main at v1, dev one commit ahead, a tag on the first commit."""

    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "afc"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.repo / "a.txt").write_text("one\n")
        self.git("add", ".")
        self.git("commit", "-qm", "one")
        self.git("tag", "v1")
        self.git("switch", "-qc", "dev")
        (self.repo / "a.txt").write_text("two\n")
        self.git("commit", "-qam", "two")
        self.git("switch", "-qc", "side", "v1")
        (self.repo / "b.txt").write_text("side\n")
        self.git("add", ".")
        self.git("commit", "-qm", "side")
        self.git("switch", "-q", "main")
        self.ctx = Context(home=self.home, root=self.repo, active=None, maintain=True, projects=())

    def git(self, *args: str) -> str:
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
        return subprocess.run(["git", *args], cwd=self.repo, env=env, check=True,
                              capture_output=True, text=True).stdout

    def reason(self, command: str, maintain: bool = True, cwd: Path | None = None) -> str | None:
        ctx = Context(home=self.home, root=self.repo, active=None, maintain=maintain, projects=())
        return check_own_copy(bash(command, cwd=cwd or self.repo), ctx)

    def test_merges_that_fast_forward_are_allowed(self):
        for maintain in (True, False):
            self.assertNotIn("fast-forward", self.reason("git merge dev", maintain) or "")
        self.assertIsNone(self.reason("git merge dev"))
        self.assertIsNone(self.reason("git merge --ff-only side"))
        self.assertIsNone(self.reason("git merge --abort"))
        self.assertIsNone(self.reason(f"git -C {self.repo} merge dev", cwd=self.tmp))

    def test_merges_that_would_not_fast_forward_are_blocked_in_every_mode(self):
        self.git("switch", "-q", "dev")
        for command in ("git merge side", "git merge --no-ff v1", "git merge --squash v1",
                        "git merge --ff-only --no-ff dev", "git merge", "git merge dev side",
                        f"git -C {self.repo} merge side"):
            self.assertIn("fast-forward", self.reason(command) or "", command)
        self.assertIsNotNone(self.reason("git merge side", maintain=False))

    def test_a_merge_git_cannot_check_is_blocked(self):
        self.assertIn("couldn't confirm", self.reason("git merge no-such-branch"))
        with mock.patch("afc.hooks.rules_maintenance.subprocess.run", side_effect=FileNotFoundError):
            self.assertIn("couldn't confirm", self.reason("git merge dev"))
            self.assertIn("detached HEAD", self.reason("git switch dev"))
        timeout = subprocess.TimeoutExpired("git", 5)
        with mock.patch("afc.hooks.rules_maintenance.subprocess.run", side_effect=timeout):
            self.assertIn("couldn't confirm", self.reason("git merge dev"))

    def test_detaching_is_blocked_and_names_the_branch(self):
        for command in ("git checkout v1", "git checkout --detach", "git switch --detach dev",
                        "git switch -d v1", "git checkout HEAD", f"git checkout {self.git('rev-parse', 'HEAD').strip()}",
                        "git switch v1", "git switch no-such-branch", "git checkout dev --detach"):
            reason = self.reason(command)
            self.assertIn("detached HEAD", reason or "", command)
            self.assertIn("main", reason)

    def test_existing_local_branches_and_file_restores_are_allowed(self):
        for command in ("git switch dev", "git switch main", "git checkout dev", "git checkout side",
                        "git checkout -- a.txt", "git checkout v1 -- a.txt", "git checkout a.txt",
                        "git checkout dev -- a.txt", "git checkout -b new", "git checkout -b new v1",
                        "git switch -c new v1", "git switch -c new", "git checkout", "git restore a.txt"):
            self.assertIsNone(self.reason(command), command)

    def test_head_rules_apply_only_in_the_a_fc_folder(self):
        other = self.tmp / "other"
        other.mkdir()
        subprocess.run(["git", "init", "-q", str(other)], check=True)
        self.assertIsNone(self.reason("git checkout v1", cwd=other))
        self.assertIsNone(self.reason("git merge --no-ff x", cwd=other))
        self.assertIsNone(self.reason(f"git -C {other} checkout --detach", cwd=self.repo))


if __name__ == "__main__":
    unittest.main()
