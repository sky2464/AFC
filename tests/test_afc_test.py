"""Tests for `sh bin/afc test`: the parallel suite runner (FC-019 slice 1)."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from afc import testrun

ROOT = Path(__file__).resolve().parent.parent

PASSING = "import unittest\n\nclass A(unittest.TestCase):\n    def test_one(self):\n        pass\n    def test_two(self):\n        pass\n"
FAILING = "import unittest\n\nclass B(unittest.TestCase):\n    def test_bad(self):\n        self.fail('nope')\n    def test_good(self):\n        pass\n"
BROKEN = "import does_not_exist_anywhere\n"


class ParallelSuiteTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="afc-fixture-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def write(self, name, body):
        (self.dir / name).write_text(body, encoding="utf-8")

    def test_passing_file_is_reported(self):
        self.write("test_pass.py", PASSING)
        out = testrun.run_files(self.dir, self.dir)
        self.assertEqual((out["files"], out["tests"], out["failed"]), (1, 2, 0))
        self.assertEqual(out["failures"], [])
        self.assertIsInstance(out["seconds"], float)

    def test_failing_file_is_reported_with_name(self):
        self.write("test_pass.py", PASSING)
        self.write("test_fail.py", FAILING)
        out = testrun.run_files(self.dir, self.dir)
        self.assertEqual((out["files"], out["tests"], out["failed"]), (2, 4, 1))
        self.assertEqual(len(out["failures"]), 1)
        self.assertIn("test_bad", out["failures"][0])

    def test_file_that_cannot_load_counts_as_failed(self):
        self.write("test_broken.py", BROKEN)
        out = testrun.run_files(self.dir, self.dir)
        self.assertEqual(out["failed"], 1)
        self.assertIn("test_broken", out["failures"][0])

    def test_command_prints_one_json_line_and_exits_nonzero_on_failure(self):
        proc = subprocess.run(["sh", str(ROOT / "bin" / "afc"), "test", "--dir", str(self.dir)],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.write("test_fail.py", FAILING)
        proc = subprocess.run(["sh", str(ROOT / "bin" / "afc"), "test", "--dir", str(self.dir)],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(proc.returncode, 1)
        lines = proc.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["failed"], 1)


if __name__ == "__main__":
    unittest.main()
