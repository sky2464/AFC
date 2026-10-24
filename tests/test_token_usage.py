import importlib.util
import json
import unittest
from pathlib import Path

from tests.helpers import AfcTestCase

SCRIPT = Path(__file__).resolve().parent.parent / "docs/measurements/token_usage.py"


def _load():
    spec = importlib.util.spec_from_file_location("token_usage", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _line(mid, i, cc, cr, out, kind="assistant"):
    usage = {"input_tokens": i, "cache_creation_input_tokens": cc,
             "cache_read_input_tokens": cr, "output_tokens": out}
    return json.dumps({"type": kind, "message": {"id": mid, "usage": usage}})


class TokenUsageTests(AfcTestCase):
    def test_sums_fresh_tokens_and_finds_peak_context(self):
        path = self.tmp / "s.jsonl"
        path.write_text("\n".join([
            _line("a", 2, 100, 50, 10),
            _line("b", 2, 20, 150, 5),
            json.dumps({"type": "user", "message": {"content": "hi"}}),
        ]), encoding="utf-8")
        r = _load().measure(path)
        self.assertEqual(r["turns"], 2)
        self.assertEqual(r["peak_context"], 172)  # 2 + 20 + 150
        self.assertEqual(r["fresh_tokens"], (2 + 100 + 10) + (2 + 20 + 5))
        self.assertEqual(r["cache_read_tokens"], 200)

    def test_repeated_message_counts_once(self):
        path = self.tmp / "s.jsonl"
        path.write_text("\n".join([_line("a", 2, 100, 50, 10), _line("a", 2, 100, 50, 10)]), encoding="utf-8")
        r = _load().measure(path)
        self.assertEqual((r["turns"], r["fresh_tokens"]), (1, 112))

    def test_skips_bad_lines(self):
        path = self.tmp / "s.jsonl"
        path.write_text("not json\n" + _line("a", 1, 1, 1, 1) + "\n{}\n", encoding="utf-8")
        self.assertEqual(_load().measure(path)["turns"], 1)


def _session(tmp, name, turns):
    """A transcript whose assistant turns are (input, cache creation, cache read, output) tuples."""
    path = tmp / name
    path.write_text("\n".join(_line(f"m{n}", *t) for n, t in enumerate(turns)), encoding="utf-8")
    return path


class FloorTests(AfcTestCase):
    """The first turn is the floor: what the session carries before Flight Control does anything."""

    def test_first_turn_is_the_floor_and_growth_is_peak_above_it(self):
        path = _session(self.tmp, "s.jsonl", [(2, 100, 50, 10), (2, 20, 150, 5)])
        r = _load().measure(path)
        self.assertEqual(r["floor_context"], 152)   # 2 + 100 + 50
        self.assertEqual(r["peak_context"], 172)
        self.assertEqual(r["growth"], 20)

    def test_added_fresh_tokens_leave_out_what_the_first_turn_read_in(self):
        path = _session(self.tmp, "s.jsonl", [(2, 100, 50, 10), (2, 20, 150, 5)])
        r = _load().measure(path)
        self.assertEqual(r["fresh_tokens"], 139)
        self.assertEqual(r["added_fresh_tokens"], 139 - (2 + 100))

    def test_the_floor_is_the_first_turn_in_file_order_not_the_smallest(self):
        path = _session(self.tmp, "s.jsonl", [(1, 0, 500, 1), (1, 0, 100, 1)])
        r = _load().measure(path)
        self.assertEqual((r["floor_context"], r["growth"]), (501, 0))

    def test_an_empty_transcript_measures_zero(self):
        path = self.tmp / "s.jsonl"
        path.write_text("", encoding="utf-8")
        r = _load().measure(path)
        self.assertEqual((r["turns"], r["floor_context"], r["growth"], r["added_fresh_tokens"]),
                         (0, 0, 0, 0))


class CompareTests(AfcTestCase):
    """Slice 4: the re-run against the baseline, judged on growth above each run's own floor."""

    def compare(self, before, after):
        return _load().compare(_session(self.tmp, "a.jsonl", before), _session(self.tmp, "b.jsonl", after))

    def test_a_third_less_growth_meets_the_target(self):
        r = self.compare([(0, 0, 1000, 0), (0, 0, 1900, 0)], [(0, 0, 1000, 0), (0, 0, 1600, 0)])
        self.assertEqual((r["growth_before"], r["growth_after"]), (900, 600))
        self.assertEqual(r["growth_target"], 600)
        self.assertTrue(r["target_met"])
        self.assertEqual(r["growth_change_percent"], -33)

    def test_less_than_a_third_does_not(self):
        r = self.compare([(0, 0, 1000, 0), (0, 0, 1900, 0)], [(0, 0, 1000, 0), (0, 0, 1700, 0)])
        self.assertFalse(r["target_met"])

    def test_a_different_floor_does_not_change_the_verdict(self):
        # The second run starts 5,000 higher (more plugins loaded) but grows the same 600.
        r = self.compare([(0, 0, 1000, 0), (0, 0, 1900, 0)], [(0, 0, 6000, 0), (0, 0, 6600, 0)])
        self.assertTrue(r["target_met"])
        self.assertEqual(r["floor_change"], 5000)

    def test_a_baseline_that_never_grew_cannot_be_compared(self):
        with self.assertRaises(ValueError):
            self.compare([(0, 0, 1000, 0)], [(0, 0, 1000, 0)])
