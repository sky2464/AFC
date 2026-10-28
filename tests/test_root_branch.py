"""The branch check reads the main checkout's branch when run from a linked worktree."""

import unittest
from pathlib import Path

from afc.cli_health import root_problems


def fake_git(branch: str, main_branch: str, linked: bool):
    """A git runner for root_problems: this copy is on `branch`; the main checkout on `main_branch`."""
    git_dir = "/repo/.git/worktrees/wt" if linked else "/repo/.git"

    def run(root: Path, *args: str) -> str | None:
        if args[:1] == ("status",):
            return f"# branch.oid abc\n# branch.head {branch}\n"
        if args == ("rev-parse", "--absolute-git-dir"):
            return git_dir + "\n"
        if args == ("rev-parse", "--path-format=absolute", "--git-common-dir"):
            return "/repo/.git\n"
        if args == ("worktree", "list", "--porcelain"):
            return (f"worktree /repo\nHEAD abc\nbranch refs/heads/{main_branch}\n\n"
                    f"worktree /wt\nHEAD def\nbranch refs/heads/{branch}\n")
        if args == ("remote",):
            return "origin\n"
        return None
    return run


def kinds(found: list[dict]) -> list[str]:
    return [p["kind"] for p in found]


class RootBranchTests(unittest.TestCase):
    def test_worktree_on_own_branch_with_main_on_dev_is_fine(self):
        found = root_problems(Path("/wt"), git=fake_git("claude/x", "dev", linked=True))
        self.assertNotIn("root_branch", kinds(found))

    def test_worktree_reports_main_checkout_off_main_or_dev(self):
        found = root_problems(Path("/wt"), git=fake_git("claude/x", "feature/y", linked=True))
        branch = [p for p in found if p["kind"] == "root_branch"]
        self.assertEqual(len(branch), 1)
        self.assertEqual(branch[0]["path"], "/repo")
        self.assertIn("feature/y", branch[0]["detail"])

    def test_main_checkout_off_main_or_dev_is_still_reported(self):
        found = root_problems(Path("/repo"), git=fake_git("feature/y", "feature/y", linked=False))
        self.assertIn("root_branch", kinds(found))

    def test_main_checkout_on_dev_is_fine(self):
        found = root_problems(Path("/repo"), git=fake_git("dev", "dev", linked=False))
        self.assertNotIn("root_branch", kinds(found))


if __name__ == "__main__":
    unittest.main()
