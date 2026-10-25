"""Structural checks for the repo's spec build workflow (FC-018 slice 1)."""

import json
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


HARNESS = r"""
const cfg = JSON.parse(process.argv[1]);
const body = require('fs').readFileSync(process.argv[2], 'utf8').replace('export const', 'const');
const calls = [];
let testRuns = 0;
const agent = async (prompt, opts) => {
  calls.push(opts.label);
  if (opts.agentType === 'afc-checker') return {pass: true, suite: 'OK', problems: [], notes: []};
  return {done: true, suite: 'OK', summary: '', commits: []};
};
const shell = async (cmd) => {
  if (cmd.startsWith('git rev-parse')) return {code: 0, out: 'abc1234\n'};
  if (cmd.startsWith('git diff --name-only')) return {code: 0, out: cfg.files.join('\n')};
  if (cmd.startsWith('git log')) return {code: 0, out: 'abc\n'};
  if (cmd.startsWith('cat ')) return {code: 0, out: '- [x] 1. done\n'};
  if (cmd.startsWith('sh bin/afc test')) {
    testRuns++;
    return {code: testRuns <= (cfg.failGate || 0) ? 1 : 0, out: 'tests'};
  }
  if (cmd.startsWith('git diff')) return {code: 0, out: cfg.diff || ''};
  return {code: 0, out: ''};
};
const fn = new Function('args', 'agent', 'log', 'phase', 'shell',
  'return (async () => {' + body + '})()');
fn(cfg.args, agent, () => {}, () => {}, shell)
  .then(r => console.log(JSON.stringify({calls, r})));
"""


def run_workflow(files, check=None, fail_gate=0, diff=""):
    args = {"spec": "docs/specs/FC-x.md", "slices": [{"number": 1, "text": "x"}]}
    if check:
        args["check"] = check
    cfg = {"files": files, "args": args, "failGate": fail_gate, "diff": diff}
    run = subprocess.run(["node", "-e", HARNESS, json.dumps(cfg), str(WORKFLOW)],
                         text=True, capture_output=True)
    if run.returncode != 0:
        raise AssertionError(run.stderr)
    return json.loads(run.stdout)


@unittest.skipUnless(shutil.which("node"), "node not installed")
class QuickGateTest(unittest.TestCase):
    def test_plain_file_runs_one_helper(self):
        out = run_workflow(["afc/plan.py"])
        self.assertEqual(out["calls"], ["build 1"])
        self.assertTrue(out["r"]["results"][0]["pass"])

    def test_risky_file_runs_checker(self):
        out = run_workflow(["afc/hooks/rules_git.py"])
        self.assertEqual(out["calls"], ["build 1", "check 1"])

    def test_check_all_checks_both(self):
        for files in (["afc/plan.py"], ["afc/hooks/rules_git.py"]):
            out = run_workflow(files, check="all")
            self.assertEqual(len(out["calls"]), 2, files)

    def test_unknown_check_value_is_refused(self):
        with self.assertRaises(AssertionError):
            run_workflow(["afc/plan.py"], check="off")

    def test_gate_failure_starts_one_fix_round(self):
        out = run_workflow(["afc/plan.py"], fail_gate=1)
        self.assertEqual(out["calls"], ["build 1", "fix 1.1"])
        self.assertTrue(out["r"]["results"][0]["pass"])

    def test_gate_catches_a_secret_in_the_diff(self):
        out = run_workflow(["afc/plan.py"], diff="+key = 'AKIAABCDEFGHIJKLMNOP'")
        self.assertFalse(out["r"]["results"][0]["pass"])
        self.assertEqual(out["calls"], ["build 1", "fix 1.1", "fix 1.2"])

    def test_gate_catches_a_file_outside_the_repo(self):
        out = run_workflow(["/etc/hosts"])
        self.assertFalse(out["r"]["results"][0]["pass"])

    def test_maintenance_mode_code_is_risky(self):
        for f in ("afc/config.py", "afc/cli_home.py"):
            out = run_workflow([f])
            self.assertIn("check 1", out["calls"], f)

    def test_every_hooks_file_is_risky(self):
        for f in sorted((ROOT / "afc" / "hooks").glob("*.py")):
            out = run_workflow([f"afc/hooks/{f.name}"])
            self.assertIn("check 1", out["calls"], f.name)


if __name__ == "__main__":
    unittest.main()
