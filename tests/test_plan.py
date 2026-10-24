"""Tests for afc.plan: master plan tables, spec ids, slices, header, compaction."""

import shutil
from pathlib import Path

from afc import config, plan
from tests.helpers import AfcTestCase

SPEC = """# S-001 — Thing

Size: M · Status: next · Started: - · Done: -

## Goal

Status: keep me

## Slices

- [ ] 1. First — you'll check it by looking
- [x] 2. Second — done
- [ ] 3. Third

## Decisions

- [ ] not a slice
"""


class PlanTestCase(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.ws = self.tmp / "ws"
        (self.ws / "plan").mkdir(parents=True)
        src = config.afc_root() / "templates/workspace/plan/master-plan.md"
        shutil.copy(src, self.ws / "plan" / plan.MASTER)

    def master(self) -> str:
        return (self.ws / "plan" / plan.MASTER).read_text(encoding="utf-8")


class RowsTests(PlanTestCase):
    def test_empty_section_has_no_rows(self):
        self.assertEqual(plan.read_rows(self.master(), "Now"), [])

    def test_round_trip(self):
        rows = [["S-001", "One", "S", "specs/S-001-one.md", "2026-01-01"]]
        text = plan.write_rows(self.master(), "Now", rows)
        self.assertEqual(plan.read_rows(text, "Now"), rows)
        self.assertEqual(plan.read_rows(text, "Next"), [])
        self.assertIn("| ID | Title | Size | Spec | Started |", text)
        self.assertEqual(plan.write_rows(text, "Now", []), self.master())

    def test_pipe_and_newline_stay_one_row(self):
        text = plan.write_rows(self.master(), "Next", [["S-001", "a|b\nc  d", "M", "x"]])
        rows = plan.read_rows(text, "Next")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "a/b c d")

    def test_cell(self):
        self.assertEqual(plan.cell(" a|b \n\n c "), "a/b c")

    def test_missing_section_raises(self):
        with self.assertRaises(ValueError):
            plan.read_rows("# Master plan\n", "Now")
        with self.assertRaises(ValueError):
            plan.write_rows("# Master plan\n", "Now", [])


class SlugTests(PlanTestCase):
    def test_slugify(self):
        self.assertEqual(plan.slugify("Health endpoint!"), "health-endpoint")
        self.assertEqual(plan.slugify("!!!"), "spec")
        s = plan.slugify("a" * 39 + " " + "b" * 40)
        self.assertEqual(s, "a" * 39)
        s = plan.slugify("word " * 30)
        self.assertLessEqual(len(s), 40)
        self.assertFalse(s.endswith("-"))


class NextIdTests(PlanTestCase):
    def test_empty(self):
        self.assertEqual(plan.next_id(self.ws), "S-001")

    def test_prefix_keeps_the_two_numberings_apart(self):
        space = plan.Space(self.ws / "plan", prefix="FC")
        self.assertEqual(plan.next_id(space), "FC-001")
        (self.ws / "plan" / "archive").mkdir(parents=True, exist_ok=True)
        (self.ws / "plan" / "archive" / "FC-004-x.md").write_text("# x\n")
        (self.ws / "plan" / "archive" / "S-030-y.md").write_text("# y\n")
        self.assertEqual(plan.next_id(space), "FC-005")
        self.assertEqual(plan.next_id(self.ws), "S-031")

    def test_flight_control_space_uses_the_fc_prefix(self):
        self.assertEqual(plan.flight_control_space(self.ws).prefix, "FC")
        self.assertEqual(plan.project_space(self.ws).prefix, "S")

    def test_no_master_plan(self):
        (self.ws / "plan" / plan.MASTER).unlink()
        self.assertEqual(plan.next_id(self.ws), "S-001")

    def test_counts_rows(self):
        text = plan.write_rows(self.master(), "Done", [["S-004", "x", "d", "l"]])
        text = plan.write_rows(text, "Next", [["S-002", "y", "M", "l"]])
        (self.ws / "plan" / plan.MASTER).write_text(text, encoding="utf-8")
        self.assertEqual(plan.next_id(self.ws), "S-005")

    def test_counts_archive_and_specs(self):
        (self.ws / "plan/archive").mkdir()
        (self.ws / "plan/specs").mkdir()
        (self.ws / "plan/archive/S-007-old.md").write_text("x")
        self.assertEqual(plan.next_id(self.ws), "S-008")
        (self.ws / "plan/specs/S-009-new.md").write_text("x")
        self.assertEqual(plan.next_id(self.ws), "S-010")

    def test_counts_archive_index(self):
        (self.ws / "plan/archive").mkdir()
        (self.ws / "plan/archive/index.md").write_text("| S-012 | t |\n")
        self.assertEqual(plan.next_id(self.ws), "S-013")


class SliceTests(PlanTestCase):
    def test_open_and_all(self):
        self.assertEqual(
            plan.open_slices(SPEC),
            ["1. First — you'll check it by looking", "3. Third"],
        )
        self.assertEqual(
            plan.all_slices(SPEC),
            [
                (False, "1. First — you'll check it by looking"),
                (True, "2. Second — done"),
                (False, "3. Third"),
            ],
        )

    def test_no_slices(self):
        self.assertEqual(plan.all_slices("## Slices\n\n## Decisions\n"), [])
        self.assertEqual(plan.open_slices("# nothing"), [])

    def test_unreadable_slices_are_list_lines_without_a_checkbox(self):
        text = "## Slices\n\n- plain one\n* star two\n3. numbered\n- [ ] fine\n  - indented note\n\n## Next\n- outside\n"
        self.assertEqual(plan.unreadable_slices(text), ["plain one", "star two", "numbered"])

    def test_checkbox_slices_are_all_readable(self):
        self.assertEqual(plan.unreadable_slices(SPEC), [])
        self.assertEqual(plan.unreadable_slices("# nothing"), [])

    def test_the_template_holds_a_readable_example_slice(self):
        template = (Path(__file__).resolve().parent.parent / "templates/workspace/spec.md").read_text(encoding="utf-8")
        self.assertEqual(len(plan.open_slices(template)), 1)
        self.assertEqual(plan.unreadable_slices(template), [])


class GoalTests(PlanTestCase):
    def test_set_goal_replaces_only_the_goal_body(self):
        text = "# Plan\n\n## Goal\n\nold words\nmore old\n\n## Now\n\n| a |\n"
        self.assertEqual(plan.set_goal(text, "New goal."),
                         "# Plan\n\n## Goal\n\nNew goal.\n\n## Now\n\n| a |\n")

    def test_set_goal_without_a_goal_section_is_an_error(self):
        with self.assertRaises(ValueError):
            plan.set_goal("# Plan\n\n## Now\n", "x")


class HeaderTests(PlanTestCase):
    def test_set_header(self):
        out = plan.set_header(SPEC, status="now", started="2026-02-01")
        self.assertIn("Size: M · Status: now · Started: 2026-02-01 · Done: -", out)
        out = plan.set_header(out, status="done", done="2026-03-01")
        self.assertIn("Size: M · Status: done · Started: 2026-02-01 · Done: 2026-03-01", out)
        self.assertIn("Status: keep me", out)

    def test_no_header_leaves_text(self):
        self.assertEqual(plan.set_header("# x\n", status="now"), "# x\n")


class LogTests(PlanTestCase):
    def test_log_appends(self):
        text = plan.log(self.master(), "2026-01-01", "first")
        text = plan.log(text, "2026-01-02", "a|b")
        self.assertEqual(
            plan.read_rows(text, "Update log"),
            [["2026-01-01", "first"], ["2026-01-02", "a/b"]],
        )


class CompactTests(PlanTestCase):
    def test_keeps_newest_done_and_all_small_logs(self):
        done = [[f"S-{i:03d}", "t", "2026-01-01", "l"] for i in range(12, 0, -1)]
        text = plan.write_rows(self.master(), "Done", done)
        (self.ws / "plan" / plan.MASTER).write_text(text, encoding="utf-8")
        plan.compact(self.ws)
        kept = plan.read_rows(self.master(), "Done")
        self.assertEqual(len(kept), 10)
        self.assertEqual(kept[0][0], "S-012")
        self.assertEqual(kept[-1][0], "S-003")

    def test_update_log_overflow_goes_to_archive(self):
        rows = [["2025-12-31", "old1"], ["2025-12-31", "old2"]]
        rows += [["2026-01-01", f"e{i}"] for i in range(100)]
        text = plan.write_rows(self.master(), "Update log", rows)
        (self.ws / "plan" / plan.MASTER).write_text(text, encoding="utf-8")
        plan.compact(self.ws)
        kept = plan.read_rows(self.master(), "Update log")
        self.assertEqual(len(kept), 100)
        self.assertEqual(kept[0], ["2026-01-01", "e0"])
        arc = (self.ws / "plan/archive/updatelog-2025.md").read_text(encoding="utf-8")
        self.assertTrue(arc.startswith("# Update log 2025\n"))
        self.assertIn("| Date | Event |", arc)
        self.assertIn("| 2025-12-31 | old1 |", arc)

    def test_archive_appends_never_overwrites(self):
        (self.ws / "plan/archive").mkdir()
        path = self.ws / "plan/archive/updatelog-2025.md"
        path.write_text("# Update log 2025\n\n| Date | Event |\n|---|---|\n| 2025-01-01 | earlier |\n")
        rows = [["2025-06-01", "moved"]] + [["2026-01-01", f"e{i}"] for i in range(100)]
        text = plan.write_rows(self.master(), "Update log", rows)
        (self.ws / "plan" / plan.MASTER).write_text(text, encoding="utf-8")
        plan.compact(self.ws)
        arc = path.read_text(encoding="utf-8")
        self.assertIn("| 2025-01-01 | earlier |", arc)
        self.assertIn("| 2025-06-01 | moved |", arc)
        self.assertEqual(arc.count("# Update log"), 1)

    def test_nothing_to_do_is_stable(self):
        before = self.master()
        plan.compact(self.ws)
        self.assertEqual(self.master(), before)
        self.assertFalse((self.ws / "plan/archive").exists())


class NowLineTests(PlanTestCase):
    def _now(self, spec_name="specs/S-001-thing.md"):
        text = plan.write_rows(self.master(), "Now", [["S-001", "Thing", "M", f"[spec]({spec_name})", "2026-01-01"]])
        (self.ws / "plan" / plan.MASTER).write_text(text, encoding="utf-8")

    def test_empty_without_plan_or_now(self):
        self.assertEqual(plan.now_line(self.ws), "")
        (self.ws / "plan" / plan.MASTER).unlink()
        self.assertEqual(plan.now_line(self.ws), "")

    def test_next_slice_all_done_and_missing_spec(self):
        self._now()
        self.assertEqual(plan.now_line(self.ws), "S-001 Thing")
        (self.ws / "plan" / "specs").mkdir()
        spec = self.ws / "plan" / "specs" / "S-001-thing.md"
        spec.write_text(SPEC, encoding="utf-8")
        self.assertEqual(plan.now_line(self.ws), "S-001 Thing (next slice: 1. First \u2014 you'll check it by looking)")
        spec.write_text("## Slices\n\n- [x] a\n", encoding="utf-8")
        self.assertEqual(plan.now_line(self.ws), "S-001 Thing (all slices done)")
