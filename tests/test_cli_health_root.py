"""The health check reads the A-FC folder's own git: a detached HEAD, uncommitted changes, a branch
that is neither main nor dev, and no origin remote. The git cases run real git in a scratch repo;
the cases where git can't run are faked."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from afc.cli_health import root_problems
from tests.helpers import AfcTestCase, run_cli
from tests.test_cli import CliTestCase

GIT_ID = ["-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "commit.gpgsign=false"]


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *GIT_ID, *args],
                          capture_output=True, text=True, check=True)
    return done.stdout


def make_repo(path: Path, branch: str = "main", origin: bool = True) -> Path:
    """A scratch repo with one commit on `branch`, shaped like a copy of Flight Control."""
    path.mkdir(parents=True)
    git(path, "init", "-q")
    git(path, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    git(path, "commit", "-q", "--allow-empty", "-m", "start")
    if origin:
        git(path, "remote", "add", "origin", "https://example.com/a-fc.git")
    return path


class RootGitTest(AfcTestCase):
    def only(self, folder: Path, kind: str) -> dict:
        found = [p for p in root_problems(folder) if p["kind"] == kind]
        self.assertEqual(len(found), 1, root_problems(folder))
        return found[0]

    def test_a_clean_main_says_nothing(self):
        self.assertEqual(root_problems(make_repo(self.tmp / "afc")), [])

    def test_a_clean_dev_says_nothing(self):
        self.assertEqual(root_problems(make_repo(self.tmp / "afc", branch="dev")), [])

    def test_a_detached_head_is_reported_in_plain_words(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "checkout", "-q", "--detach")
        git(folder, "commit", "-q", "--allow-empty", "-m", "stray")
        found = self.only(folder, "root_detached")
        self.assertFalse(found["fixable"])
        self.assertEqual(found["path"], str(folder))
        self.assertIn("detached HEAD", found["detail"])
        self.assertIn("not on main", found["detail"])

    def test_an_untracked_file_is_uncommitted_change(self):
        folder = make_repo(self.tmp / "afc")
        (folder / "notes.txt").write_text("draft\n", encoding="utf-8")
        found = self.only(folder, "root_dirty")
        self.assertFalse(found["fixable"])
        self.assertIn("uncommitted changes", found["detail"])

    def test_an_edited_tracked_file_is_uncommitted_change(self):
        folder = make_repo(self.tmp / "afc")
        (folder / "a.txt").write_text("one\n", encoding="utf-8")
        git(folder, "add", "a.txt")
        git(folder, "commit", "-q", "-m", "add a")
        (folder / "a.txt").write_text("two\n", encoding="utf-8")
        self.only(folder, "root_dirty")

    def test_files_git_ignores_are_not_changes(self):
        # Flight Control writes .claude/settings.local.json into its own folder; that is not work to keep
        folder = make_repo(self.tmp / "afc")
        (folder / ".gitignore").write_text(".claude/settings.local.json\n", encoding="utf-8")
        git(folder, "add", ".gitignore")
        git(folder, "commit", "-q", "-m", "ignore")
        (folder / ".claude").mkdir()
        (folder / ".claude" / "settings.local.json").write_text("{}", encoding="utf-8")
        self.assertEqual(root_problems(folder), [])

    def test_a_branch_that_is_neither_main_nor_dev_is_reported(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "checkout", "-q", "-b", "feature")
        found = self.only(folder, "root_branch")
        self.assertFalse(found["fixable"])
        self.assertIn("feature", found["detail"])
        self.assertIn("neither main nor dev", found["detail"])

    def test_a_missing_origin_is_reported(self):
        folder = make_repo(self.tmp / "afc", origin=False)
        found = self.only(folder, "root_no_origin")
        self.assertFalse(found["fixable"])
        self.assertIn("origin", found["detail"])

    def test_a_remote_under_another_name_is_not_origin(self):
        folder = make_repo(self.tmp / "afc", origin=False)
        git(folder, "remote", "add", "upstream", "https://example.com/a-fc.git")
        self.only(folder, "root_no_origin")

    def test_git_that_cannot_run_reports_nothing(self):
        with patch("afc.cli_health.subprocess.run", side_effect=FileNotFoundError("git")):
            self.assertEqual(root_problems(self.tmp / "afc"), [])

    def test_git_that_hangs_reports_nothing(self):
        with patch("afc.cli_health.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 3)):
            self.assertEqual(root_problems(self.tmp / "afc"), [])

    def test_a_folder_that_is_not_a_repo_reports_nothing(self):
        self.assertEqual(root_problems(self.tmp), [])

    def test_git_runs_in_the_folder_with_a_short_timeout(self):
        folder = self.tmp / "afc"
        with patch("afc.cli_health.subprocess.run", side_effect=FileNotFoundError("git")) as run:
            root_problems(folder)
        self.assertEqual(run.call_args.args[0][:3], ["git", "-C", str(folder)])
        self.assertLessEqual(run.call_args.kwargs["timeout"], 5)

    def test_the_git_runner_can_be_passed_in(self):
        answers = {("status", "--porcelain=v2", "--branch"): "# branch.head (detached)\n",
                   ("remote",): "origin\n"}
        found = root_problems(self.tmp / "afc", git=lambda root, *args: answers.get(args))
        self.assertEqual([p["kind"] for p in found], ["root_detached"])


class RootCheckTest(CliTestCase):
    """sh bin/afc check shows the A-FC folder's problems next to the registry's."""

    def check(self, folder: Path) -> dict:
        with patch("afc.cli.afc_root", return_value=folder):
            rc, out = run_cli(["check"])
        self.assertEqual(rc, 0, out)
        return out

    def test_check_names_a_detached_copy_in_plain_words(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "checkout", "-q", "--detach")
        out = self.check(folder)
        self.assertFalse(out["ok"])
        found = [p for p in out["problems"] if p["kind"] == "root_detached"]
        self.assertEqual(len(found), 1)
        self.assertIn("detached HEAD", found[0]["detail"])

    def test_check_says_nothing_about_git_on_a_clean_main(self):
        self.assertEqual(self.check(make_repo(self.tmp / "afc")), {"ok": True, "problems": []})

    def test_check_says_once_when_git_cannot_run(self):
        folder = make_repo(self.tmp / "afc")
        with patch("afc.cli_health.subprocess.run", side_effect=FileNotFoundError("git")):
            out = self.check(folder)
        self.assertEqual(out["problems"], [])
        self.assertIn("Git couldn't run", out["note"])
        self.assertEqual(out["note"].count("Git couldn't run"), 1)


class RootRepairTest(CliTestCase):
    """sh bin/afc repair puts a clean detached copy whose commit is on main back onto main."""

    def repair(self, folder: Path) -> dict:
        with patch("afc.cli.afc_root", return_value=folder):
            rc, out = run_cli(["repair"])
        self.assertEqual(rc, 0, out)
        return out

    def kinds(self, out: dict) -> list[str]:
        return [p["kind"] for p in out["left"]]

    def head(self, folder: Path) -> str:
        return git(folder, "rev-parse", "--abbrev-ref", "HEAD").strip()

    def test_a_clean_detached_copy_on_main_is_switched_back(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "checkout", "-q", "--detach")
        self.assertTrue(next(p for p in root_problems(folder) if p["kind"] == "root_detached")["fixable"])
        out = self.repair(folder)
        self.assertEqual(self.head(folder), "main")
        self.assertIn("Put Flight Control's own copy back on main.", out["repaired"])
        self.assertEqual(out["left"], [])

    def test_an_older_commit_on_main_is_switched_back(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "commit", "-q", "--allow-empty", "-m", "second")
        git(folder, "checkout", "-q", "--detach", "HEAD~1")
        self.repair(folder)
        self.assertEqual(self.head(folder), "main")

    def test_a_dirty_detached_copy_is_left_untouched_with_a_reason(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "checkout", "-q", "--detach")
        (folder / "notes.txt").write_text("draft\n", encoding="utf-8")
        out = self.repair(folder)
        self.assertEqual(self.head(folder), "HEAD")
        self.assertEqual((folder / "notes.txt").read_text(encoding="utf-8"), "draft\n")
        self.assertEqual(out["repaired"], [])
        detached = next(p for p in out["left"] if p["kind"] == "root_detached")
        self.assertFalse(detached["fixable"])
        self.assertIn("uncommitted changes", detached["detail"])

    def test_a_commit_not_on_main_is_left_untouched_with_a_reason(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "checkout", "-q", "--detach")
        git(folder, "commit", "-q", "--allow-empty", "-m", "stray")
        stray = git(folder, "rev-parse", "HEAD").strip()
        out = self.repair(folder)
        self.assertEqual(git(folder, "rev-parse", "HEAD").strip(), stray)
        self.assertEqual(self.head(folder), "HEAD")
        detached = next(p for p in out["left"] if p["kind"] == "root_detached")
        self.assertFalse(detached["fixable"])
        self.assertIn("not on main", detached["detail"])

    def test_a_commit_only_on_dev_is_left_alone(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "checkout", "-q", "-b", "dev")
        git(folder, "commit", "-q", "--allow-empty", "-m", "dev work")
        git(folder, "checkout", "-q", "--detach")
        self.repair(folder)
        self.assertEqual(self.head(folder), "HEAD")

    def test_a_copy_with_no_main_branch_is_left_alone(self):
        folder = make_repo(self.tmp / "afc", branch="dev")
        git(folder, "checkout", "-q", "--detach")
        out = self.repair(folder)
        self.assertEqual(self.head(folder), "HEAD")
        self.assertIn("root_detached", self.kinds(out))

    def test_git_that_cannot_run_changes_nothing(self):
        folder = make_repo(self.tmp / "afc")
        git(folder, "checkout", "-q", "--detach")
        with patch("afc.cli_health.subprocess.run", side_effect=FileNotFoundError("git")):
            out = self.repair(folder)
        self.assertEqual(out, {"repaired": [], "left": []})
        self.assertEqual(self.head(folder), "HEAD")
