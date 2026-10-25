"""FC-015 slice 4: a WIP commit and an unpushed branch each fail the gate, naming the user's step."""

import subprocess
from pathlib import Path

from tests.helpers import run_cli
from tests.test_cli import CliTestCase

PASS = "python3 -c 'import sys; sys.exit(0)'"


def git(code, *args):
    return subprocess.run(["git", "-c", "user.name=a", "-c", "user.email=a@b.c", *args], cwd=code,
                          capture_output=True, text=True, check=True).stdout


class ShipGitTest(CliTestCase):
    def setUp(self):
        super().setUp()
        rc, out = self.new()
        self.assertEqual(rc, 0)
        self.ws = Path(out["workspace_path"])
        self.code = Path(out["code_path"])
        run_cli(["plan", "add", "Thing"])
        run_cli(["plan", "start", "S-001"])
        spec = next((self.ws / "plan" / "specs").glob("S-001-*.md"))
        text = spec.read_text(encoding="utf-8").replace("- [ ] 1.", "- [x] 1.")
        spec.write_text(text, encoding="utf-8")
        (self.ws / "plan" / "architecture.md").write_text(f"Test command: {PASS}\n", encoding="utf-8")
        self.commit("first")

    def commit(self, msg):
        git(self.code, "add", "-A")
        git(self.code, "commit", "-q", "--allow-empty", "-m", msg)

    def missing(self):
        rc, out = run_cli(["ship", "--check", "S-001"])
        self.assertEqual(rc, 0, out)
        return out["missing"]

    def add_remote(self):
        bare = self.code.parent / (self.code.name + "-remote.git")
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        git(self.code, "remote", "add", "origin", str(bare))
        return bare

    def test_wip_commit_fails_and_names_the_user_step(self):
        self.commit("WIP: half done")
        items = self.missing()
        self.assertEqual(len(items), 1)
        self.assertIn("WIP", items[0])
        self.assertIn("rebase", items[0])

    def test_lowercase_wip_prefix_also_fails(self):
        self.commit("wip fix")
        self.assertIn("WIP", self.missing()[0])

    def test_word_containing_wip_is_fine(self):
        self.commit("Add wiping of caches")
        self.assertEqual(self.missing(), [])

    def test_no_remote_means_no_push_check(self):
        self.assertEqual(self.missing(), [])

    def test_unpushed_branch_fails_with_push_step(self):
        self.add_remote()
        items = self.missing()
        self.assertEqual(len(items), 1)
        self.assertIn("not pushed", items[0])
        self.assertIn("git push", items[0])

    def test_pushed_branch_passes_and_new_commit_fails(self):
        self.add_remote()
        branch = git(self.code, "rev-parse", "--abbrev-ref", "HEAD").strip()
        git(self.code, "push", "-q", "-u", "origin", branch)
        self.assertEqual(self.missing(), [])
        self.commit("later")
        self.assertIn("not pushed", self.missing()[0])
