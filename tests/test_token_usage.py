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
    """Slice 4: the re-run against a like-for-like control, judged on growth above each run's own
    floor. The target is 10% less growth than the control's (a third was out of reach by trimming)."""

    def compare(self, before, after):
        return _load().compare(_session(self.tmp, "a.jsonl", before), _session(self.tmp, "b.jsonl", after))

    def test_ten_percent_less_growth_meets_the_target(self):
        r = self.compare([(0, 0, 1000, 0), (0, 0, 1900, 0)], [(0, 0, 1000, 0), (0, 0, 1810, 0)])
        self.assertEqual((r["growth_before"], r["growth_after"]), (900, 810))
        self.assertEqual(r["growth_target"], 810)
        self.assertTrue(r["target_met"])
        self.assertEqual(r["growth_change_percent"], -10)

    def test_less_than_ten_percent_does_not(self):
        r = self.compare([(0, 0, 1000, 0), (0, 0, 1900, 0)], [(0, 0, 1000, 0), (0, 0, 1811, 0)])
        self.assertEqual(r["growth_after"], 811)
        self.assertFalse(r["target_met"])

    def test_the_target_is_ninety_percent_of_the_controls_growth(self):
        r = self.compare([(0, 0, 1000, 0), (0, 0, 2000, 0)], [(0, 0, 1000, 0), (0, 0, 1900, 0)])
        self.assertEqual((r["growth_before"], r["growth_target"]), (1000, 900))
        self.assertTrue(r["target_met"])  # exactly 900: at or below counts
        r = self.compare([(0, 0, 1000, 0), (0, 0, 2000, 0)], [(0, 0, 1000, 0), (0, 0, 1901, 0)])
        self.assertFalse(r["target_met"])  # 901: one over

    def test_a_third_less_is_no_longer_what_is_asked(self):
        # 600 against a 900 control is a third less; the target only needs 810.
        r = self.compare([(0, 0, 1000, 0), (0, 0, 1900, 0)], [(0, 0, 1000, 0), (0, 0, 1600, 0)])
        self.assertTrue(r["target_met"])
        self.assertEqual(r["growth_change_percent"], -33)

    def test_a_different_floor_does_not_change_the_verdict(self):
        # The second run starts 5,000 higher (more plugins loaded) but grows only 800.
        r = self.compare([(0, 0, 1000, 0), (0, 0, 1900, 0)], [(0, 0, 6000, 0), (0, 0, 6800, 0)])
        self.assertTrue(r["target_met"])
        self.assertEqual(r["floor_change"], 5000)

    def test_a_control_that_never_grew_cannot_be_compared(self):
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

    def test_a_control_that_is_not_a_whole_run_is_refused_too(self):
        self.assertRefused("control", "commit the slice", before_ran=FULL_RUN[:2])

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


def _turn(mid, context, tools=(), text=False):
    """One assistant turn with a prompt of `context` tokens and the given tool calls (name, input)."""
    content = [{"type": "text", "text": "ok"}] if text else []
    content += [{"type": "tool_use", "name": n, "input": i} for n, i in tools]
    usage = {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": context,
             "output_tokens": 1}
    return json.dumps({"type": "assistant", "message": {"id": mid, "usage": usage, "content": content}})


class BreakdownTests(AfcTestCase):
    """Slice 1 of FC-017: growth by part, each jump credited to the turn before it."""

    def parts(self, turns):
        path = self.tmp / "b.jsonl"
        path.write_text("\n".join(turns), encoding="utf-8")
        return _load().breakdown(path)

    def test_each_part_gets_the_jump_after_its_turn(self):
        # The prompt of turn n holds what turn n-1 added, so the jump is credited to turn n-1.
        r = self.parts([
            _turn("m0", 1000, tools=[("Write", {"file_path": "/app/server.py"})]),         # code +10
            _turn("m1", 1010, tools=[("Edit", {"file_path": "/app/tests/test_x.py"})]),    # code +20
            _turn("m2", 1030, text=True),                                                   # replies +3
            _turn("m3", 1033, tools=[("Skill", {"skill": "afc-slice"})]),                   # skill +10
            _turn("m4", 1043, tools=[("Edit", {"file_path": "/h/docs/specs/FC-1-x.md"})]),  # plan +20
            _turn("m5", 1063, tools=[("Write", {"file_path": "/h/.A-FC/projects/p/plan.md"})]),  # plan +1
            _turn("m6", 1064, tools=[("Read", {"file_path": "/app/a.py"})]),                # read +5
            _turn("m7", 1069, tools=[("Bash", {"command": "sh bin/afc status"})]),          # other +10
            _turn("m8", 1079, text=True),
        ])
        self.assertEqual(r["code_and_tests"], 30)
        self.assertEqual(r["replies"], 3)
        self.assertEqual(r["skill_text"], 10)
        self.assertEqual(r["plan_and_spec_edits"], 21)
        self.assertEqual(r["files_read"], 5)
        self.assertEqual(r["other"], 10)
        self.assertEqual(r["growth"], 79)

    def test_the_parts_add_up_to_growth_and_stop_at_the_peak(self):
        r = self.parts([_turn("m0", 1000, text=True), _turn("m1", 1100, text=True),
                        _turn("m2", 1050, text=True)])
        self.assertEqual(r["growth"], 100)
        self.assertEqual(sum(r[k] for k in _load().PARTS), 100)

    def test_a_turn_split_over_lines_is_read_once_with_all_its_tools(self):
        first = json.loads(_turn("m1", 1000, tools=[("Read", {"file_path": "/a"})]))
        second = json.loads(_turn("m1", 1000, tools=[("Write", {"file_path": "/app/x.py"})]))
        r = self.parts([_turn("m0", 1000, text=True), json.dumps(first), json.dumps(second),
                        _turn("m2", 1010, text=True)])
        self.assertEqual(r["replies"], 0)
        self.assertEqual(r["code_and_tests"], 10)

    def test_reading_a_skill_file_counts_as_skill_text(self):
        r = self.parts([_turn("m0", 1000, tools=[("Read", {"file_path": "/A-FC/skills/afc-slice/SKILL.md"})]),
                        _turn("m1", 1007)])
        self.assertEqual(r["skill_text"], 7)

    def test_an_empty_transcript_has_zero_parts(self):
        r = self.parts([])
        self.assertTrue(all(r[k] == 0 for k in _load().PARTS))

    def test_the_command_line_prints_the_parts_with_the_breakdown_flag(self):
        path = self.tmp / "c.jsonl"
        path.write_text("\n".join([_turn("m0", 1000), _turn("m1", 1010, text=True), _turn("m2", 1010)]),
                        encoding="utf-8")
        done = subprocess.run([sys.executable, str(SCRIPT), "--parts", str(path)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)
        out = json.loads(done.stdout)
        self.assertEqual((out["replies"], out["growth"]), (10, 10))
