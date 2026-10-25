"""The build workflow's quick gate command (FC-019 fix)."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from afc import gate


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


class QuickGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@t")
        git(self.root, "config", "user.name", "t")
        self.spec = self.root / "spec.md"
        self.spec.write_text("- [ ] 1. thing\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        self.base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.root, capture_output=True,
                                   text=True).stdout.strip()

    def commit(self, message, tick=True, extra=""):
        self.spec.write_text("- [x] 1. thing\n" if tick else "- [ ] 1. thing\n")
        (self.root / "a.txt").write_text(extra or "hello\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", message)

    def test_a_tagged_ticked_clean_slice_is_ok(self):
        self.commit("FC-x slice 1: thing")
        out = gate.quick_gate(self.root, self.spec, 1, self.base)
        self.assertTrue(out["ok"], out["problems"])
        self.assertEqual(sorted(out["files"]), ["a.txt", "spec.md"])

    def test_untagged_commit_and_unticked_box_are_problems(self):
        self.commit("did stuff", tick=False)
        said = " ".join(p["problem"] for p in gate.quick_gate(self.root, self.spec, 1, self.base)["problems"])
        self.assertIn('"slice 1"', said)
        self.assertIn("not ticked", said)

    def test_a_secret_in_the_diff_is_a_problem(self):
        self.commit("slice 1", extra="key = 'AKIAABCDEFGHIJKLMNOP'\n")
        out = gate.quick_gate(self.root, self.spec, 1, self.base)
        self.assertTrue(any("secret" in p["problem"] for p in out["problems"]))

    def test_an_unknown_base_is_one_problem_not_a_crash(self):
        out = gate.quick_gate(self.root, self.spec, 1, "nope")
        self.assertFalse(out["ok"])
        self.assertEqual(len(out["problems"]), 1)


if __name__ == "__main__":
    unittest.main()
