"""slice record ticks the spec, logs the decision and notes the architecture (FC-020 slice 3)."""

from pathlib import Path
from unittest.mock import patch

from tests.helpers import run_cli
from tests.test_cli import CliTestCase


class SliceRecordTest(CliTestCase):
    def setUp(self):
        super().setUp()
        rc, out = self.new()
        self.assertEqual(rc, 0)
        self.plan = Path(out["workspace_path"]) / "plan"
        run_cli(["plan", "add", "Thing"])
        self.spec = next((self.plan / "specs").glob("S-001-*.md"))
        text = self.spec.read_text(encoding="utf-8").replace(
            "- [ ] 1. <label> — you'll check it by <how>\n", "- [ ] 1. first — by a\n- [ ] 2. second — by b\n")
        self.spec.write_text(text, encoding="utf-8")

    def files(self):
        return [p.read_bytes() for p in (self.spec, self.plan / "decisions.md", self.plan / "architecture.md")]

    def record(self, n=1):
        return run_cli(["slice", "record", "S-001", str(n), "--decision", "Used SQLite", "--architecture", "Added store"])

    def test_one_call_writes_three_files(self):
        rc, out = self.record()
        self.assertEqual(rc, 0)
        spec = self.spec.read_text(encoding="utf-8")
        self.assertIn("- [x] 1. first", spec)
        self.assertIn("- [ ] 2. second", spec)
        dec = (self.plan / "decisions.md").read_text(encoding="utf-8")
        self.assertIn("S-001 slice 1\nUsed SQLite", dec)
        self.assertGreater(dec.index("S-001 slice 1"), dec.index("## Log"))
        arch = (self.plan / "architecture.md").read_text(encoding="utf-8")
        self.assertIn("S-001 slice 1: Added store", arch)
        self.assertGreater(arch.index("Added store"), arch.index("## 9. Decision links"))
        self.assertLess(arch.index("Added store"), arch.index("## 10."))

    def test_unknown_slice_is_refused_and_nothing_changes(self):
        before = self.files()
        rc, out = self.record(7)
        self.assertNotEqual(rc, 0)
        self.assertIn("no slice 7", out["error"])
        self.assertEqual(self.files(), before)

    def test_unknown_spec_is_refused_and_nothing_changes(self):
        before = self.files()
        rc, out = run_cli(["slice", "record", "S-009", "1", "--decision", "x", "--architecture", "y"])
        self.assertNotEqual(rc, 0)
        self.assertEqual(self.files(), before)
