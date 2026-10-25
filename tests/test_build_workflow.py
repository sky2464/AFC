"""Structural checks for the repo's spec build workflow (FC-018 slice 1)."""

import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".claude" / "workflows" / "afc-build-spec.js"


class BuildWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(WORKFLOW.is_file(), f"missing {WORKFLOW}")
        self.text = WORKFLOW.read_text()

    def test_starts_with_meta(self):
        self.assertTrue(self.text.startswith("export const meta = {"))

    def test_reads_its_inputs(self):
        for name in ("args.spec", "args.slices", "args.builder", "args.checker"):
            self.assertIn(name, self.text)

    def test_names_no_particular_spec(self):
        self.assertIsNone(re.search(r"FC-0\d\d", self.text))

    def test_one_checker_per_round(self):
        self.assertEqual(self.text.count("agent(checkPrompt"), 1)
        self.assertNotIn("parallel(", self.text)
        self.assertIsNone(re.search(r"label:\s*[`'\"]suite", self.text))

    def test_at_most_two_fix_rounds(self):
        self.assertIn("const MAX_FIX_ROUNDS = 2", self.text)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_body_parses(self):
        body = self.text.replace("export const", "const", 1)
        src = "(async () => {\n" + body + "\n})\n"
        run = subprocess.run(["node", "--check", "-"], input=src, text=True,
                             capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    unittest.main()
