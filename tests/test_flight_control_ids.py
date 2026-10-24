"""Flight Control's own specs use FC- IDs, so they can't be mistaken for a project's S- specs."""

import re
import unittest
from pathlib import Path

from afc import plan

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


class FlightControlIdsTest(unittest.TestCase):
    def setUp(self):
        self.text = (DOCS / plan.MASTER).read_text(encoding="utf-8")

    def spec_rows(self):
        return [r for section in ("Now", "Next") for r in plan.read_rows(self.text, section)]

    def test_plan_rows_use_fc_ids(self):
        rows = self.spec_rows()
        self.assertTrue(rows)
        for row in rows:
            self.assertRegex(row[0], r"^FC-\d{3}$")
            self.assertFalse(re.match(r"^S-\d{3}$", row[0]))

    def test_spec_files_match_their_rows_and_headings(self):
        files = sorted(p for p in (DOCS / "specs").glob("*.md"))
        self.assertTrue(files)
        for path in files:
            self.assertRegex(path.name, r"^FC-\d{3}-")
            sid = path.name[:6]
            self.assertTrue(path.read_text(encoding="utf-8").startswith(f"# {sid} \u2014 "), path.name)
        linked = {re.search(r"\(([^)]*)\)", r[3]).group(1) for r in self.spec_rows()}
        self.assertEqual(linked, {f"specs/{p.name}" for p in files})

    def test_findings_tables_point_at_fc_specs(self):
        pointers = re.findall(r"\|\s*(FC-\d{3}|S-\d{3})\s*\|\s*$", self.text, re.M)
        self.assertTrue(pointers)
        self.assertEqual([p for p in pointers if p.startswith("S-")], [])

    def test_the_real_plan_numbers_the_next_spec_after_the_last(self):
        highest = max(int(n) for n in re.findall(r"\bFC-(\d{3})\b", self.text))
        self.assertEqual(plan.next_id(plan.flight_control_space(ROOT)), f"FC-{highest + 1:03d}")


if __name__ == "__main__":
    unittest.main()
