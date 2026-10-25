import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import AfcTestCase

SCRIPT = Path(__file__).resolve().parent.parent / "docs/measurements/token_usage.py"


def _load():
    spec = importlib.util.spec_from_file_location("token_usage", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _line(mid, i, cc, cr, out, kind="assistant", commands=()):
    usage = {"input_tokens": i, "cache_creation_input_tokens": cc,
             "cache_read_input_tokens": cr, "output_tokens": out}
    message = {"id": mid, "usage": usage}
    if commands:
        message["content"] = [{"type": "tool_use", "name": "Bash", "input": {"command": c}} for c in commands]
    return json.dumps({"type": kind, "message": message})


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


FULL_RUN = ("sh bin/afc new --name demo", "sh bin/afc scan --slice 1", "sh bin/afc deliver --message x")


def _session(tmp, name, turns, ran=FULL_RUN):
    """A transcript whose assistant turns are (input, cache creation, cache read, output) tuples.

    The commands in `ran` are run on the last turn, so by default the session shows a whole start
    plus first slice: the project created, the slice checked, the slice committed.
    """
    lines = []
    for n, t in enumerate(turns):
        lines.append(_line(f"m{n}", *t, commands=ran if n == len(turns) - 1 else ()))
    path = tmp / name
    path.write_text("\n".join(lines), encoding="utf-8")
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


GROWTH = [(0, 0, 1000, 0), (0, 0, 1500, 0), (0, 0, 1700, 0), (0, 0, 1900, 0)]


class WholeRunTests(AfcTestCase):
    """A re-run only counts when it is a whole start plus first slice (a session that said "hi" once
    once passed as a 95% saving)."""

    def compare(self, before_ran=FULL_RUN, after_ran=FULL_RUN, after=GROWTH):
        return _load().compare(_session(self.tmp, "a.jsonl", GROWTH, ran=before_ran),
                               _session(self.tmp, "b.jsonl", after, ran=after_ran))

    def assertRefused(self, who, *missing, **kwargs):
        with self.assertRaises(ValueError) as caught:
            self.compare(**kwargs)
        message = str(caught.exception)
        self.assertTrue(message.startswith(f"The {who} "), message)
        for words in missing:
            self.assertIn(words, message)
        return message

    def test_steps_reached_lists_the_steps_in_start_to_finish_order(self):
        path = _session(self.tmp, "s.jsonl", GROWTH, ran=("sh bin/afc scan --slice 1", "sh bin/afc new --name d"))
        self.assertEqual(_load().steps_reached(path), ["new", "scan"])

    def test_a_whole_run_is_compared(self):
        self.assertEqual(self.compare()["growth_after"], 900)

    def test_a_session_that_only_said_hi_is_refused(self):
        message = self.assertRefused("re-run", "create the project", "check the slice", "commit the slice", after_ran=())
        self.assertIn("compare again", message)

    def test_a_run_that_stops_before_the_commit_is_refused(self):
        message = self.assertRefused("re-run", "commit the slice", after_ran=FULL_RUN[:2])
        self.assertNotIn("create the project", message)

    def test_a_run_that_never_created_the_project_is_refused(self):
        self.assertRefused("re-run", "create the project", after_ran=FULL_RUN[1:])

    def test_a_baseline_that_is_not_a_whole_run_is_refused_too(self):
        self.assertRefused("baseline", "commit the slice", before_ran=FULL_RUN[:2])

    def test_other_commands_do_not_count(self):
        self.assertRefused("re-run", "create the project", after_ran=("git status", "sh bin/afc status"))

    def test_talking_about_a_command_does_not_count(self):
        path = self.tmp / "talk.jsonl"
        said = {"type": "assistant", "message": {"id": "t", "usage": {"input_tokens": 1}, "content": [
            {"type": "text", "text": "I will run sh bin/afc new, then bin/afc scan and bin/afc deliver"}]}}
        path.write_text(json.dumps(said), encoding="utf-8")
        self.assertEqual(_load().steps_reached(path), [])

    def test_a_command_with_a_full_path_counts(self):
        path = _session(self.tmp, "s.jsonl", GROWTH,
                        ran=("sh /Users/x/A-FC-test/bin/afc new --name d", "sh ~/A-FC/bin/afc scan --slice 1",
                             "cd /tmp && sh /Users/x/A-FC-test/bin/afc deliver --message m"))
        self.assertEqual(_load().steps_reached(path), ["new", "scan", "deliver"])

    def test_a_command_run_through_a_variable_set_to_the_afc_path_counts(self):
        # A session working in the project's folder keeps Flight Control's path in a variable.
        path = _session(self.tmp, "s.jsonl", GROWTH,
                        ran=("sh bin/afc new --name d", "A=/Users/x/A-FC-test/bin/afc\nsh $A scan --slice 1",
                             'SH=~/A-FC/bin/afc; sh "${SH}" deliver --message m'))
        self.assertEqual(_load().steps_reached(path), ["new", "scan", "deliver"])

    def test_a_variable_that_is_not_the_afc_path_does_not_count(self):
        path = _session(self.tmp, "s.jsonl", GROWTH,
                        ran=("X=/usr/bin/other sh $X deliver --message m", "sh $Y new --name d",
                             "A=/x/bin/afc\nsh $B scan", "A=/x/bin/afc"))
        self.assertEqual(_load().steps_reached(path), [])

    def test_the_command_line_prints_a_plain_error_and_exits_1(self):
        before = _session(self.tmp, "a.jsonl", GROWTH)
        after = _session(self.tmp, "b.jsonl", GROWTH, ran=())
        done = subprocess.run([sys.executable, str(SCRIPT), str(before), str(after)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertNotIn("Traceback", done.stderr)
        self.assertTrue(json.loads(done.stdout)["error"].startswith("The re-run "))

    def test_one_transcript_is_still_measured_without_the_check(self):
        path = _session(self.tmp, "s.jsonl", GROWTH, ran=())
        done = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
        self.assertEqual((done.returncode, json.loads(done.stdout)["turns"]), (0, 4))
