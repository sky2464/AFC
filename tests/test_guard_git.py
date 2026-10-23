import subprocess
from pathlib import Path
from unittest.mock import patch

from afc.hooks.common import Context
from afc.hooks.rules_git import check_git, scan_commit_text, staged_diff
from tests.helpers import FIXTURES_DIR, AfcTestCase, bash, ev

BLOCKED = ["git push --force origin main", "cd app && git push -f", "git reset --hard HEAD~1",
           "git clean -fd", "git branch -D old", "git rebase -i main", "gh repo create x --public",
           "gh repo create x", "gh repo edit --visibility public", "terraform apply -var env=prod",
           "kubectl apply -f k8s/ --context production", "git commit --amend -m x",
           "git push origin +main", "git -C /x reset --hard", "git checkout .",
           "docker push img:prd", "az devops project create p --visibility public",
           # formatting bypasses
           "git  reset --hard", "git\treset --hard", "git reset HEAD~1 --hard", "git clean -d -f",
           "git clean --force", "git checkout -- .", "git restore -- .",
           "git --no-pager reset --hard", 'git -C "/a b" reset --hard', "git push origin :main",
           "sh -c 'git reset --hard'"]
ALLOWED = ["git push origin main", "git commit -m 'feat: x'", "gh repo create x --private --source .",
           "terraform apply -var env=dev", "git status", "kubectl get pods",
           "git push origin main && rm -f build.log", "git push && echo a+b",
           'docker push img && echo "not prod"', 'git commit -m "mention git rebase and --public"',
           "git rebase --abort", "git rebase --continue", "git rebase --quit",
           "cat > notes.md <<'EOF'\ngit rebase -i\ngh repo create x --public\nEOF"]

REVIEW_PACKAGE = FIXTURES_DIR / "review-package"  # vendored copy of a real commented script

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

    def commit_tracked_then_edit(self, text):
        self.stage("clean\n")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
        (self.repo / "f.txt").write_text(text)

    def test_commit_forms_scan_unstaged(self):
        self.commit_tracked_then_edit(f"key = {SECRET}\n")
        for c in ["git commit -a -m x", "git commit -am x", "git commit --all -m x",
                  "git commit -i f.txt -m x", "git commit -o f.txt -m x", "git commit f.txt -m x",
                  "git commit -m x -- f.txt"]:
            self.assertIsNotNone(check_git(bash(c, cwd=self.repo), self.ctx), c)
        self.assertIsNone(check_git(bash("git commit -m x", cwd=self.repo), self.ctx))

    def test_commit_repo_located_through_global_options(self):
        self.stage(f"key = {SECRET}\n")
        r = self.repo
        for c in [f"git --git-dir={r}/.git --work-tree={r} commit -m x",
                  f"git --git-dir {r}/.git --work-tree {r} commit -m x",
                  "git --no-pager commit -m x", "sh -c 'git commit -m x'", "xargs git commit -m x"]:
            self.assertIsNotNone(check_git(bash(c, cwd=r), self.ctx), c)

    def test_commit_unlocatable_blocks(self):
        self.assertIsNotNone(check_git(bash("find . -exec git commit -m x ;", cwd=self.repo), self.ctx))
        self.assertIsNotNone(check_git(bash("git -C $NOPE_UNSET commit -m x", cwd=self.repo), self.ctx))

    def test_staged_diff_keeps_plus_plus_lines(self):
        self.stage("++plus\n+++ also\n")
        self.assertEqual(staged_diff(self.repo), "++plus\n+++ also")

    def test_scan_commit_text_seam(self):
        self.assertIsNone(scan_commit_text("hello"))
        self.assertIsNotNone(scan_commit_text(SECRET))

    def test_prod_token_must_share_command(self):
        self.assertIsNone(check_git(bash("terraform apply && echo prod"), self.ctx))
        self.assertIsNotNone(check_git(bash("echo x && kubectl --context prd apply -f k"), self.ctx))

    def test_combined_shell_flags_followed(self):
        for flag in ("-lc", "-ec", "-ic", "-xec"):
            for sh in ("bash", "sh", "zsh", "dash"):
                c = f"{sh} {flag} 'git reset --hard'"
                self.assertIsNotNone(check_git(bash(c), self.ctx), c)
        self.stage(f"key = {SECRET}\n")
        self.assertIsNotNone(check_git(bash("bash -lc 'git commit -m x'", cwd=self.repo), self.ctx))

    def test_eval_followed(self):
        self.assertIsNotNone(check_git(bash("eval 'git reset --hard'"), self.ctx))
        self.assertIsNotNone(check_git(bash("eval git reset --hard"), self.ctx))
        self.assertIsNotNone(check_git(bash("eval \"echo 'unclosed\""), self.ctx))
        self.assertIsNone(check_git(bash("eval 'git status'"), self.ctx))

    def test_failed_cd_still_scans_commit(self):
        self.stage(f"key = {SECRET}\n")
        c = f"cd /nope-afc-missing; git -C {self.repo} commit -m x"
        self.assertIsNotNone(check_git(bash(c, cwd=self.tmp), self.ctx))

    def test_shell_forms_followed_or_blocked(self):
        for c in ["bash -c -- 'git reset --hard'", "sudo -u x bash -c 'git reset --hard'",
                  "ksh -c 'git reset --hard'", "busybox sh -c 'git reset --hard'",
                  "echo 'git reset --hard' | bash", "bash <<< 'git status'", "bash < run.sh",
                  "bash script.sh", "bash", "env -u X bash -c 'git rebase'"]:
            self.assertIsNotNone(check_git(bash(c), self.ctx), c)
        for c in ["bash -c 'git status'", "bash -c -o pipefail 'git status'",
                  "sudo -u x ls", "env -i A=1 git status", "ls -la"]:
            self.assertIsNone(check_git(bash(c), self.ctx), c)

    def test_script_files_followed(self):
        d = self.tmp / "scripts"
        d.mkdir()
        (d / "ok.sh").write_text("git status\n")
        (d / "bad.sh").write_text("git reset --hard\n")
        (d / "bin.sh").write_bytes(b"git status\0\xff")
        (d / "inner.sh").write_text("git reset --hard\n")
        (d / "outer.sh").write_text("bash inner.sh\n")
        for i in range(5):  # l4 runs git status; l2 is 3 scripts deep, l1 is 4
            (d / f"l{i}.sh").write_text(f"bash l{i + 1}.sh\n" if i < 4 else "git status\n")
        for c in ["bash ok.sh", "source ok.sh", ". ok.sh", "bash -e ok.sh arg",
                  "sh -- ok.sh", f"bash {d}/ok.sh", "bash l2.sh"]:
            self.assertIsNone(check_git(bash(c, cwd=d), self.ctx), c)
        self.assertIsNone(check_git(bash(f"cd {d} && bash ok.sh", cwd=self.tmp), self.ctx))
        for c in ["bash bad.sh", "source bad.sh", ". bad.sh", "bash missing.sh",
                  "bash bin.sh", "bash outer.sh", "bash l1.sh", "bash -s ok.sh",
                  "cat ok.sh | bash", "bash < ok.sh", "source"]:
            self.assertIsNotNone(check_git(bash(c, cwd=d), self.ctx), c)

    def test_comments_stripped(self):
        script = Path(REVIEW_PACKAGE).read_text()
        (self.tmp / "rp").write_text(script)
        self.assertIsNone(check_git(bash(f"bash {self.tmp}/rp a b c", cwd=self.tmp), self.ctx))
        (self.tmp / "s.sh").write_text("#!/usr/bin/env bash\n# it's (named per range).\ngit status\n")
        self.assertIsNone(check_git(bash("bash s.sh", cwd=self.tmp), self.ctx))
        for c in ["echo $# && git status", "echo hi # git reset --hard", "echo ${#x}"]:
            self.assertIsNone(check_git(bash(c), self.ctx), c)
        for c in ["echo x#y; git reset --hard", "echo '# q'; git reset --hard",
                  "# note\ngit reset --hard"]:
            self.assertIsNotNone(check_git(bash(c), self.ctx), c)

    def test_sudo_long_options_skipped(self):
        for c in ["sudo --user x bash -c 'git reset --hard'", "sudo --group g git reset --hard",
                  "sudo --chdir /tmp --prompt p git reset --hard", "sudo --user=x git reset --hard",
                  "sudo --close-from 3 --role r --type t --host h --other-user u git reset --hard"]:
            self.assertIsNotNone(check_git(bash(c), self.ctx), c)
        self.assertIsNone(check_git(bash("sudo --user x git status"), self.ctx))

    def test_env_split_string_inspected(self):
        for c in ["env -S 'git reset --hard'", "env --split-string 'git reset --hard'",
                  "env --split-string='git reset --hard'", "env -S\"git reset --hard\"",
                  "env -S \"bash -c 'git reset --hard'\" x", "env -S \"echo 'open\""]:
            self.assertIsNotNone(check_git(bash(c), self.ctx), c)
        self.assertIsNone(check_git(bash("env -S 'git status'"), self.ctx))

    def test_more_wrappers_followed(self):
        for c in ["timeout 5 git reset --hard", "timeout -s KILL -k 2 5s git reset --hard",
                  "nice -n 5 git reset --hard", "nice git reset --hard", "stdbuf -oL git reset --hard",
                  "stdbuf -o L git reset --hard", "ionice -c 3 git reset --hard",
                  "doas -u x git reset --hard", "chronic git reset --hard",
                  "nohup git reset --hard", "xargs -n 1 -I {} git reset --hard",
                  "timeout 5 bash -c 'git reset --hard'", "nice -n 1 timeout 3 xargs git clean -fd"]:
            self.assertIsNotNone(check_git(bash(c), self.ctx), c)
        for c in ["timeout 5 git status", "nice -n 5 ls", "xargs -n 1 echo"]:
            self.assertIsNone(check_git(bash(c), self.ctx), c)

    def test_commit_outside_repo_allowed(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        self.assertIsNone(check_git(bash("git commit -m x", cwd=plain), self.ctx))

    def test_git_missing_blocks(self):
        with patch("afc.hooks.rules_git.subprocess.run", side_effect=FileNotFoundError("git")):
            self.assertIsNotNone(check_git(bash("git commit -m x", cwd=self.repo), self.ctx))
