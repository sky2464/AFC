"""Git that changes the A-FC folder needs maintenance mode; git that only reads never does."""

import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
