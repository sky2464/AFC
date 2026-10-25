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

    def test_uses_nothing_the_workflow_runtime_lacks(self):
        # The runtime has no import(), require or process; the gate runs commands through a helper.
        self.assertIsNone(re.search(r"\bimport\(|\brequire\(|\bprocess\.", self.text))

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
let gateRuns = 0;
let finalRuns = 0;
const agent = async (prompt, opts) => {
  calls.push(opts.label);
  if (opts.agentType === 'afc-checker') return {pass: true, suite: 'OK', problems: [], notes: []};
  return {done: true, suite: 'OK', summary: '', commits: []};
};
const shell = async (cmd) => {
  if (cmd.startsWith('git rev-parse')) return {code: 0, out: 'a'.repeat(40) + '\n'};
  if (cmd.startsWith('sh bin/afc gate')) {
    gateRuns++;
    const bad = gateRuns <= (cfg.failGate || 0);
    return {code: 0, out: JSON.stringify({ok: !bad, files: cfg.files,
      problems: bad ? [{problem: 'x', quotes: 'q'}] : []})};
  }
  if (cmd.startsWith('git diff --name-only')) return {code: 0, out: cfg.files.join('\n')};
  if (cmd.startsWith('git log')) return {code: 0, out: 'abc\n'};
  if (cmd.startsWith('cat "tests/')) return {code: 0, out: cfg.testText || ''};
  if (cmd.startsWith('cat ')) return {code: 0, out: '- [x] 1. done\n- [x] 2. done\n'};
  if (cmd === 'sh bin/afc test') {
    finalRuns++;
    if (finalRuns <= (cfg.failFinal || 0)) {
      return {code: 1, out: JSON.stringify({failed: 1, failures: [cfg.failTest + ': FAIL: test_x']})};
    }
    return {code: 0, out: JSON.stringify({failed: 0, failures: []})};
  }
  if (cmd.startsWith('git diff')) return {code: 0, out: cfg.diff || ''};
  return {code: 0, out: ''};
};
const fn = new Function('args', 'agent', 'log', 'phase', 'shell',
  'return (async () => {' + body + '})()');
fn(cfg.args, agent, () => {}, () => {}, shell)
  .then(r => console.log(JSON.stringify({calls, r})));
"""


def run_workflow(files, check=None, fail_gate=0, diff="", slices=1, fail_final=0,
                 fail_test="test_a.py", test_text="", files_by_slice=None):
    args = {"spec": "docs/specs/FC-x.md",
            "slices": [{"number": n, "text": "x"} for n in range(1, slices + 1)]}
    if check:
        args["check"] = check
    cfg = {"files": files, "args": args, "failGate": fail_gate, "diff": diff,
           "failFinal": fail_final, "failTest": fail_test, "testText": test_text}
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

    def test_maintenance_mode_code_is_risky(self):
        for f in ("afc/config.py", "afc/cli_home.py"):
            out = run_workflow([f])
            self.assertIn("check 1", out["calls"], f)

    def test_every_hooks_file_is_risky(self):
        for f in sorted((ROOT / "afc" / "hooks").glob("*.py")):
            out = run_workflow([f"afc/hooks/{f.name}"])
            self.assertIn("check 1", out["calls"], f.name)


@unittest.skipUnless(shutil.which("node"), "node not installed")
class FinalSuiteTest(unittest.TestCase):
    def test_passing_final_suite_starts_no_helper(self):
        out = run_workflow(["afc/plan.py"])
        self.assertEqual(out["calls"], ["build 1"])
        self.assertTrue(out["r"]["finalSuite"]["ok"])

    def test_failing_final_suite_starts_one_fixer_and_one_checker(self):
        out = run_workflow(["afc/plan.py"], fail_final=1)
        self.assertEqual(out["calls"], ["build 1", "fix 1.final1", "check 1.final1"])
        self.assertTrue(out["r"]["finalSuite"]["ok"])

    def test_failure_goes_to_the_slice_that_changed_the_code(self):
        out = run_workflow(["afc/plan.py"], slices=2, fail_final=1, test_text="import afc.plan")
        self.assertEqual(out["calls"][2:], ["fix 1.final1", "check 1.final1"])

    def test_unmatched_failure_goes_to_the_last_slice(self):
        out = run_workflow(["afc/plan.py"], slices=2, fail_final=1, test_text="nothing")
        self.assertEqual(out["calls"][2:], ["fix 2.final1", "check 2.final1"])

    def test_at_most_two_rounds(self):
        out = run_workflow(["afc/plan.py"], fail_final=5)
        self.assertEqual(len(out["calls"]), 1 + 2 * 2)
        self.assertFalse(out["r"]["finalSuite"]["ok"])


class NewCommandTest(unittest.TestCase):
    def test_no_helper_or_contributing_says_unittest_discover(self):
        for path in (ROOT / ".claude" / "agents" / "afc-builder.md",
                     ROOT / ".claude" / "agents" / "afc-checker.md",
                     ROOT / "CONTRIBUTING.md"):
            self.assertNotIn("unittest discover", path.read_text(), path.name)


if __name__ == "__main__":
    unittest.main()
