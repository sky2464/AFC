import subprocess
from unittest.mock import patch

from afc.hooks.common import Context
from afc.hooks.rules_git import check_git, staged_diff
from tests.helpers import AfcTestCase, bash, ev

BLOCKED = ["git push --force origin main", "cd app && git push -f", "git reset --hard HEAD~1",
           "git clean -fd", "git branch -D old", "git rebase -i main", "gh repo create x --public",
           "gh repo create x", "gh repo edit --visibility public", "terraform apply -var env=prod",
           "kubectl apply -f k8s/ --context production", "git commit --amend -m x",
           "git push origin +main", "git -C /x reset --hard", "git checkout .",
           "docker push img:prd", "az devops project create p --visibility public"]
ALLOWED = ["git push origin main", "git commit -m 'feat: x'", "gh repo create x --private --source .",
           "terraform apply -var env=dev", "git status", "kubectl get pods"]

SECRET = "AKIA" + "ABCDEFGHIJKLMNOP"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True)


class TestGitRule(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.ctx = Context(home=self.home, root=self.tmp, active=None, maintain=False)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")

    def stage(self, text):
        (self.repo / "f.txt").write_text(text)
        git(self.repo, "add", "f.txt")

    def test_blocked(self):
        for c in BLOCKED:
            self.assertIsNotNone(check_git(bash(c), self.ctx), c)

    def test_allowed(self):
        self.stage("hello\n")
        for c in ALLOWED:
            self.assertIsNone(check_git(bash(c, cwd=self.repo), self.ctx), c)

    def test_reason_names_category(self):
        self.assertIn("git", check_git(bash("git reset --hard"), self.ctx))
        self.assertIn("public", check_git(bash("gh repo create x --public"), self.ctx))
        self.assertIn("production", check_git(bash("terraform apply prod"), self.ctx))

    def test_non_bash_ignored(self):
        self.assertIsNone(check_git(ev("Write", {"file_path": "/tmp/x", "content": "git rebase"}), self.ctx))

    def test_staged_diff_added_lines_only(self):
        self.stage("one\ntwo\n")
        self.assertEqual(staged_diff(self.repo), "one\ntwo")

    def test_commit_with_staged_secret_blocked(self):
        self.stage(f"key = {SECRET}\n")
        reason = check_git(bash("git commit -m x", cwd=self.repo), self.ctx)
        self.assertIsNotNone(reason)
        self.assertNotIn(SECRET, reason)

    def test_commit_with_git_dash_c_path(self):
        self.stage(f"key = {SECRET}\n")
        self.assertIsNotNone(check_git(bash(f"git -C {self.repo} commit -m x"), self.ctx))
        self.assertIsNotNone(check_git(bash(f"cd {self.repo} && git commit -m x"), self.ctx))

    def test_commit_outside_repo_allowed(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        self.assertIsNone(check_git(bash("git commit -m x", cwd=plain), self.ctx))

    def test_git_missing_blocks(self):
        with patch("afc.hooks.rules_git.subprocess.run", side_effect=FileNotFoundError("git")):
            self.assertIsNotNone(check_git(bash("git commit -m x", cwd=self.repo), self.ctx))
