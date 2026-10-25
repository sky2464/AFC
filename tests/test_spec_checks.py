"""Checks that quote the spec (FC-018 slice 3)."""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".claude" / "workflows" / "afc-build-spec.js"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"


def sort_problems(check):
    text = WORKFLOW.read_text()
    fn = re.search(r"function sortProblems\(check\) \{.*?\n\}", text, re.S).group(0)
    src = fn + "\nconsole.log(JSON.stringify(sortProblems(" + json.dumps(check) + ")))"
    run = subprocess.run(["node", "-e", src], text=True, capture_output=True, check=True)
    return json.loads(run.stdout)


class SpecChecksTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_unquoted_problem_becomes_note(self):
        out = sort_problems({"pass": False, "suite": "OK", "notes": ["n"], "problems": [
            {"problem": "tied", "quotes": "never delays the welcome"},
            {"problem": "loose", "quotes": "  "},
        ]})
        self.assertEqual([p["problem"] for p in out["problems"]], ["tied"])
        self.assertEqual(out["notes"], ["n", "loose"])
        self.assertFalse(out["pass"])

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_only_notes_can_pass(self):
        out = sort_problems({"pass": True, "suite": "OK", "notes": [], "problems": [
            {"problem": "style", "quotes": ""}]})
        self.assertTrue(out["pass"])
        self.assertEqual(out["problems"], [])

    def test_checker_schema_keeps_them_apart(self):
        text = WORKFLOW.read_text()
        self.assertIn("required: ['problem', 'quotes']", text)
        self.assertIn("required: ['pass', 'suite', 'problems', 'notes']", text)

    def test_contributing_asks_for_numbers(self):
        text = CONTRIBUTING.read_text()
        self.assertIn("## Writing specs", text)
        section = text.split("## Writing specs", 1)[1].split("\n## ", 1)[0]
        for word in ("time, size or count", "number", "you'll check it by"):
            self.assertIn(word, section)


if __name__ == "__main__":
    unittest.main()
