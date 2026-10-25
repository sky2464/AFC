"""Tests for the SessionStart welcome hook."""

import io
import json
import socket
import subprocess
import time
from pathlib import Path
from unittest import mock

from afc import update
from afc.config import set_maintain
from afc.hooks import session_start
from afc.hooks.session_start import BANNER, INTRO, build_output, main
from afc.registry import Project, Registry, save_registry
from tests.helpers import AfcTestCase, RemoteCase, git, run_cli

ROOT = Path(__file__).resolve().parent.parent


class SessionStartTest(AfcTestCase):
    def _ctx(self, out):
        return out["hookSpecificOutput"]["additionalContext"]

    def test_first_run(self):
        out = build_output(self.home)
        self.assertEqual(
            out["systemMessage"],
            f"{INTRO}\nType 1 to start a new project, 2 to bring in one already on this computer, "
            "or just say hi.")
        self.assertTrue(out["systemMessage"].startswith("✈️  Flight Control"))
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")
        ctx = self._ctx(out)
        self.assertIn("Active project: none — first run.", ctx)
        self.assertIn("The welcome asked: 1 = start a new project, "
                      "2 = bring in one already on this computer.", ctx)

    def test_context_names_the_launcher_by_absolute_path(self):
        from afc.config import afc_root
        launcher = str(afc_root() / "bin" / "afc")
        self.assertIn(f"sh {launcher}", self._ctx(build_output(self.home)))
        with mock.patch("afc.hooks.session_start.maintain_enabled", return_value=True):
            self.assertIn(f"sh {launcher}", self._ctx(build_output(self.home)))

    def test_projects_but_none_active(self):
        reg = Registry()
        reg.add(Project(name="kong-gateway-lab", code_path="/c", workspace_path="/w"))
        save_registry(self.home, reg)
        out = build_output(self.home)
        self.assertEqual(
            out["systemMessage"],
            f"{INTRO}\nWelcome back. Type 1 to pick one of your projects, 2 to start a new project, "
            "or just say hi.")
        ctx = self._ctx(out)
        self.assertIn("Active project: none. Other projects: kong-gateway-lab.", ctx)
        self.assertIn("1 = pick one of your projects, 2 = start a new project.", ctx)

    def test_returning_user(self):
        reg = Registry()
        reg.add(Project(name="kong-gateway-lab", code_path="/c/kong", workspace_path="/w/kong",
                        profile="api", last_slice="add rate limit"))
        reg.add(Project(name="other-app", code_path="/c/o", workspace_path="/w/o"))
        reg.set_active("kong-gateway-lab")
        save_registry(self.home, reg)
        ctx = self._ctx(build_output(self.home))
        self.assertIn(
            "Active project: kong-gateway-lab (api), code: /c/kong, workspace: /w/kong, "
            "last slice: add rate limit. Other projects: other-app.", ctx)
        self.assertIn("afc-start skill", ctx)
        self.assertIn("1 = continue kong-gateway-lab, 2 = something else.", ctx)
        self.assertTrue(build_output(self.home)["systemMessage"].endswith(
            "Welcome back. Type 1 to continue kong-gateway-lab (last: add rate limit), "
            "2 for something else, or just say hi."))

    def test_returning_user_sees_active_spec(self):
        from afc.workspace import create_workspace
        from afc import plan
        ws = create_workspace(self.home, "kong-gateway-lab")
        master = ws / "plan" / plan.MASTER
        master.write_text(plan.write_rows(master.read_text(encoding="utf-8"), "Now",
                          [["S-001", "Thing", "M", "[spec](specs/none.md)", "2026-01-01"]]), encoding="utf-8")
        reg = Registry()
        reg.add(Project(name="kong-gateway-lab", code_path="/c", workspace_path=str(ws)))
        reg.set_active("kong-gateway-lab")
        save_registry(self.home, reg)
        self.assertIn(" Active spec: S-001 Thing.", self._ctx(build_output(self.home)))

    def test_only_paused_projects(self):
        reg = Registry()
        reg.add(Project(name="kong-gateway-lab", code_path="/c", workspace_path="/w", status="paused"))
        save_registry(self.home, reg)
        out = build_output(self.home)
        self.assertTrue(out["systemMessage"].endswith(
            "Welcome back. Type 1 to resume a paused project, 2 to start a new project, "
            "or just say hi."))
        ctx = self._ctx(out)
        self.assertIn("Active project: none. Other projects: none. Paused: kong-gateway-lab.", ctx)
        self.assertIn("1 = resume a paused project, 2 = start a new project.", ctx)

    def test_paused_projects_are_not_picked(self):
        reg = Registry()
        reg.add(Project(name="old-app", code_path="/c", workspace_path="/w", status="paused"))
        reg.add(Project(name="new-app", code_path="/c2", workspace_path="/w2"))
        save_registry(self.home, reg)
        ctx = self._ctx(build_output(self.home))
        self.assertIn("Other projects: new-app. Paused: old-app.", ctx)
        self.assertIn("1 = pick one of your projects", ctx)

    def test_long_last_slice_is_shortened(self):
        reg = Registry()
        reg.add(Project(name="app", code_path="/c", workspace_path="/w",
                        last_slice="add a health endpoint that reports database and cache status"))
        reg.set_active("app")
        save_registry(self.home, reg)
        line = build_output(self.home)["systemMessage"].splitlines()[-1]
        self.assertIn("(last: add a health endpoint that reports data…)", line)

    def test_no_last_slice_and_no_others(self):
        reg = Registry()
        reg.add(Project(name="solo-app", code_path="/c", workspace_path="/w"))
        reg.set_active("solo-app")
        save_registry(self.home, reg)
        ctx = self._ctx(build_output(self.home))
        self.assertIn("last slice: none. Other projects: none.", ctx)

    def test_welcome_with_corrupt_registry(self):
        (self.home / "projects.json").write_text("{")
        out = build_output(self.home)
        self.assertEqual(out["systemMessage"], BANNER)
        self.assertIn("Registry unreadable", self._ctx(out))
        self.assertIn("offer to repair it", self._ctx(out))

    def test_unexpected_error_still_valid(self):
        with mock.patch.object(session_start, "load_registry", side_effect=RuntimeError("boom")):
            out = build_output(self.home)
        self.assertEqual(out["systemMessage"], BANNER)
        self.assertIn("Registry unreadable: boom", self._ctx(out))

    def test_main_always_zero(self):
        buf = io.StringIO()
        self.assertEqual(main(buf), 0)
        self.assertTrue(json.loads(buf.getvalue())["systemMessage"].startswith(INTRO))
        (self.home / "projects.json").write_text("{")
        buf = io.StringIO()
        self.assertEqual(main(buf), 0)
        self.assertIn("Registry unreadable", json.loads(buf.getvalue())["hookSpecificOutput"]["additionalContext"])


class TestHomeLineTest(AfcTestCase):
    """Claude is told about a workspace folder that isn't ~/.A-FC; the welcome stays clean."""

    def welcome(self, env):
        buf = io.StringIO()
        with mock.patch.dict("os.environ", env):
            self.assertEqual(main(buf), 0)
        return json.loads(buf.getvalue())

    def test_other_home_is_in_the_context_only(self):
        out = self.welcome({"AFC_HOME": str(self.home)})
        self.assertNotIn("Test home", out["systemMessage"])
        self.assertIn(f"test home {self.home.resolve()}",
                      out["hookSpecificOutput"]["additionalContext"])

    def test_default_home_adds_nothing(self):
        default = self.tmp / ".A-FC"
        out = self.welcome({"HOME": str(self.tmp), "AFC_HOME": str(default)})
        self.assertNotIn("Test home", out["systemMessage"])
        self.assertNotIn("test home", out["hookSpecificOutput"]["additionalContext"])


NOW = 1_000_000.0
DAY = 86400
FIRST_RUN = (f"{INTRO}\nType 1 to start a new project, 2 to bring in one already on this computer, "
             "or just say hi.")
OFFER = (f"{INTRO}\nFlight Control v0.02a is out; you have v0.01a.\n"
         "1. Update now (recommended)  2. Not now")


class UpdateOfferTest(RemoteCase):
    """FC-011 slice 3: the welcome offers a newer release. The copy here is a clone of a test remote
    on main at v0.01a, so it is not a developer copy."""

    def setUp(self):
        super().setUp()
        for name, value in (("afc_root", self.copy), ("_health_line", "")):
            patcher = mock.patch.object(session_start, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def welcome(self, now=NOW):
        return build_output(self.home, now=now)

    def message(self, now=NOW):
        return self.welcome(now)["systemMessage"]

    def context(self, now=NOW):
        return self.welcome(now)["hookSpecificOutput"]["additionalContext"]

    def skip(self, tag):
        with mock.patch("afc.cli_version.afc_root", return_value=self.copy):
            return run_cli(["update", "--skip", tag])

    def add_project(self):
        reg = Registry()
        reg.add(Project(name="kong-gateway-lab", code_path="/c/kong", workspace_path="/w/kong",
                        profile="api", last_slice="add rate limit"))
        reg.set_active("kong-gateway-lab")
        save_registry(self.home, reg)

    # -- the offer

    def test_an_older_copy_is_offered_the_update(self):
        self.tag("v0.02a")
        self.assertEqual(self.message(), OFFER)

    def test_the_notice_is_one_line_and_names_both_versions(self):
        self.tag("v0.10a")
        notice = self.message().splitlines()[len(INTRO.splitlines())]
        self.assertEqual(notice, "Flight Control v0.10a is out; you have v0.01a.")

    def test_the_options_are_update_now_recommended_and_not_now(self):
        self.tag("v0.02a")
        options = self.message().splitlines()[-1]
        self.assertTrue(options.startswith("1. Update now (recommended)"), options)
        self.assertTrue(options.endswith("2. Not now"), options)

    def test_the_project_question_waits_for_the_update_question(self):
        self.tag("v0.02a")
        self.add_project()
        message = self.message()
        self.assertNotIn("Type 1", message)
        self.assertNotIn("kong-gateway-lab", message)
        ctx = self.context()
        self.assertIn("The welcome asked the update question first", ctx)
        self.assertNotIn("The welcome asked: 1 =", ctx)

    def test_the_context_tells_claude_what_1_and_2_mean(self):
        self.tag("v0.02a")
        ctx = self.context()
        self.assertIn("release is out: v0.02a (installed v0.01a)", ctx)
        self.assertIn("1 = update now, 2 = not now", ctx)
        self.assertIn("sh bin/afc update --skip v0.02a", ctx)
        self.assertIn("sh bin/afc update ", ctx)
        self.assertIn("afc-start skill", ctx)

    def test_the_context_still_has_the_projects_for_the_question_that_follows(self):
        self.tag("v0.02a")
        self.add_project()
        ctx = self.context()
        self.assertIn("Active project: kong-gateway-lab (api)", ctx)
        self.assertIn("1 = continue kong-gateway-lab, 2 = something else", ctx)

    def test_the_context_keeps_the_launcher_and_the_health_note(self):
        self.tag("v0.02a")
        note = " Health check: 1 problem (sh bin/afc check)."
        with mock.patch.object(session_start, "_health_line", return_value=note):
            ctx = self.context()
        self.assertIn("Run Flight Control with: sh ", ctx)
        self.assertIn(note, ctx)

    def test_main_prints_the_offer_and_exits_zero(self):
        self.tag("v0.02a")
        buf = io.StringIO()
        self.assertEqual(main(buf), 0)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["systemMessage"], OFFER)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")

    # -- nothing to offer

    def test_no_newer_release_the_welcome_is_as_usual(self):
        self.assertEqual(self.message(), FIRST_RUN)
        self.assertIn("The welcome asked: 1 = start a new project", self.context())
        self.assertNotIn("update", self.context().lower().replace("sh bin/afc", ""))

    def test_a_copy_already_on_the_newest_release_hears_nothing(self):
        (self.copy / "VERSION").write_text("v0.02a\n")
        self.tag("v0.02a")
        self.assertEqual(self.message(), FIRST_RUN)

    def test_offline_says_nothing(self):
        self.tag("v0.02a")
        self.go_offline()
        self.assertEqual(self.welcome(), build_output(self.home, now=NOW))
        self.assertEqual(self.message(), FIRST_RUN)

    def test_a_tag_that_is_not_a_release_says_nothing(self):
        self.tag("nightly", "release-9")
        self.assertEqual(self.message(), FIRST_RUN)

    def test_a_missing_version_file_says_nothing(self):
        self.tag("v0.02a")
        (self.copy / "VERSION").unlink()
        self.assertEqual(self.message(), FIRST_RUN)

    def test_a_check_that_blows_up_never_breaks_the_welcome(self):
        self.tag("v0.02a")
        with mock.patch("afc.update.check", side_effect=RuntimeError("boom")):
            self.assertEqual(self.message(), FIRST_RUN)

    def test_a_check_with_an_odd_answer_never_breaks_the_welcome(self):
        for answer in (None, [], "available", {"update": "available"}, {"update": "available", "latest": 5}):
            with self.subTest(answer=answer), mock.patch("afc.update.check", return_value=answer):
                self.assertEqual(self.message(), FIRST_RUN)

    def test_an_unreadable_registry_is_not_held_up_by_a_check(self):
        self.tag("v0.02a")
        (self.home / "projects.json").write_text("{")
        with mock.patch("afc.update.check") as check:
            out = self.welcome()
        self.assertEqual(out["systemMessage"], BANNER)
        check.assert_not_called()

    # -- Not now

    def test_not_now_stays_quiet_on_the_next_start(self):
        self.tag("v0.02a")
        self.assertEqual(self.message(), OFFER)
        code, out = self.skip("v0.02a")
        self.assertEqual((code, out), (0, {"skipped": "v0.02a"}))
        self.assertEqual(self.message(), FIRST_RUN)

    def test_not_now_stays_quiet_after_the_daily_check_runs_again(self):
        self.tag("v0.02a")
        self.message()
        self.skip("v0.02a")
        for days in (1, 2, 30):
            with self.subTest(days=days):
                self.assertEqual(self.message(now=NOW + days * DAY + 60), FIRST_RUN)

    def test_not_now_speaks_up_again_when_a_newer_release_comes_out(self):
        self.tag("v0.02a")
        self.message()
        self.skip("v0.02a")
        self.tag("v0.03a")
        self.assertEqual(self.message(now=NOW + 2 * DAY), OFFER.replace("v0.02a", "v0.03a"))

    def test_not_now_for_a_newer_release_than_the_one_found_stays_quiet(self):
        self.tag("v0.02a")
        self.skip("v0.05a")
        self.assertEqual(self.message(), FIRST_RUN)

    # -- developer copies

    def test_a_developer_copy_on_dev_never_hears_about_updates(self):
        self.tag("v0.02a")
        git(self.copy, "switch", "-qc", "dev")
        self.assertEqual(self.message(), FIRST_RUN)

    def test_maintenance_mode_never_checks_or_offers(self):
        self.tag("v0.02a")
        set_maintain(self.home, True)
        with mock.patch("afc.update.check") as check:
            message = self.message()
        check.assert_not_called()
        self.assertIn("Maintenance", message)
        self.assertNotIn("v0.02a", message)
        self.assertNotIn("Update now", message)

    # -- once a day

    def test_the_second_start_of_the_day_uses_the_saved_answer(self):
        self.tag("v0.02a")
        self.assertEqual(self.message(), OFFER)
        self.go_offline()
        self.assertEqual(self.message(now=NOW + 3600), OFFER)

    def test_the_next_day_asks_the_remote_again(self):
        self.tag("v0.02a")
        self.assertEqual(self.message(), OFFER)
        self.go_offline()
        self.assertEqual(self.message(now=NOW + DAY + 60), FIRST_RUN)

    # -- never delays the welcome

    def test_the_budget_is_short(self):
        self.assertLessEqual(session_start.WELCOME_BUDGET, 3)
        self.assertLessEqual(session_start.WELCOME_BUDGET, update.TIMEOUT)

    def test_every_git_call_of_the_check_gets_the_short_budget(self):
        calls = []
        real_run = subprocess.run

        def slow(*args, **kwargs):
            if kwargs.get("env", {}).get("GIT_TERMINAL_PROMPT") != "0":
                return real_run(*args, **kwargs)  # not one of the update check's git calls
            calls.append(kwargs["timeout"])
            raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

        with mock.patch("afc.update.subprocess.run", side_effect=slow):
            self.assertEqual(self.message(), FIRST_RUN)
        self.assertTrue(calls)
        self.assertLessEqual(max(calls), session_start.WELCOME_BUDGET)

    def test_a_check_that_found_the_remote_fast_still_uses_the_short_budget_for_every_call(self):
        self.tag("v0.02a")
        calls = []
        real_run = subprocess.run

        def spy(*args, **kwargs):
            if kwargs.get("env", {}).get("GIT_TERMINAL_PROMPT") == "0":
                calls.append((args[0][1:3], kwargs["timeout"]))
            return real_run(*args, **kwargs)

        with mock.patch("afc.update.subprocess.run", side_effect=spy):
            self.assertEqual(self.message(), OFFER)
        self.assertGreaterEqual(len(calls), 4)  # branch, tags, fetch, history
        self.assertLessEqual(max(t for _, t in calls), session_start.WELCOME_BUDGET)

    def test_a_remote_that_never_answers_does_not_hold_up_the_welcome(self):
        silent = socket.socket()
        silent.bind(("127.0.0.1", 0))
        silent.listen(5)
        self.addCleanup(silent.close)
        git(self.copy, "remote", "set-url", "origin", f"http://127.0.0.1:{silent.getsockname()[1]}/a.git")
        with mock.patch.object(session_start, "WELCOME_BUDGET", 0.5):
            started = time.monotonic()
            message = self.message()
            took = time.monotonic() - started
        self.assertEqual(message, FIRST_RUN)
        self.assertLess(took, 3, f"the welcome waited {took:.1f}s for a silent remote")

    def test_a_slow_check_is_not_repeated_on_every_start(self):
        silent = socket.socket()
        silent.bind(("127.0.0.1", 0))
        silent.listen(5)
        self.addCleanup(silent.close)
        git(self.copy, "remote", "set-url", "origin", f"http://127.0.0.1:{silent.getsockname()[1]}/a.git")
        with mock.patch.object(session_start, "WELCOME_BUDGET", 0.5), \
                mock.patch.object(update, "remote_newest", wraps=update.remote_newest) as looked:
            self.message()
            self.message(now=NOW + 60)
            self.message(now=NOW + 3600)
        self.assertEqual(looked.call_count, 1)


class AfcStartSkillTest(AfcTestCase):
    """The start skill tells Claude what to do with the answer to the update question."""

    def skill(self):
        return (ROOT / ".claude" / "skills" / "afc-start" / "SKILL.md").read_text(encoding="utf-8")

    def test_the_skill_handles_the_update_question(self):
        text = self.skill()
        self.assertIn("newer release", text)
        self.assertIn("1. Update now (recommended)", text)
        self.assertIn("2. Not now", text)
        self.assertIn("sh bin/afc update --skip", text)
        self.assertIn("sh bin/afc update`", text)

    def test_the_update_question_comes_before_the_project_question(self):
        text = self.skill()
        self.assertLess(text.index("newer release"), text.index("**Projects but none active**"))
