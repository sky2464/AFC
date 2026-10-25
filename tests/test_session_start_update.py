"""Tests for the update offer in the SessionStart welcome (FC-011 slice 3).

They sit apart from tests/test_session_start.py, which would otherwise pass the size ceiling.
"""

import io
import json
import socket
import subprocess
import time
from unittest import mock

from afc import update
from afc.config import set_maintain
from afc.hooks import session_start
from afc.hooks.session_start import BANNER, INTRO, build_output, main
from afc.registry import Project, Registry, save_registry
from tests.helpers import RemoteCase, git, run_cli

NOW = 1_000_000.0
DAY = 86400
FIRST_RUN = (f"{INTRO}\nType 1 to start a new project, 2 to bring in one already on this computer, "
             "or just say hi.")
OFFER = (f"{INTRO}\nFlight Control v0.02a is out; you have v0.01a.\n"
         "1. Update now (recommended)  2. Not now")


class WelcomeCase(RemoteCase):
    """A welcome built over a clone of a test remote on main at v0.01a, so it is not a developer
    copy. start() is one start of a session."""

    def setUp(self):
        super().setUp()
        for name, value in (("afc_root", self.copy), ("_health_line", "")):
            patcher = mock.patch.object(session_start, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def start(self, now=NOW):
        return build_output(self.home, now=now)


class UpdateOfferTest(WelcomeCase):
    """FC-011 slice 3: the welcome offers a newer release. It answers from what the daily look for a
    release saved; the look itself is a background process, which these tests stand in for: look()
    finishes the ones the starts began, as they would a moment later."""

    def setUp(self):
        super().setUp()
        self.looks = []
        patcher = mock.patch.object(
            update, "start_refresh", side_effect=lambda *look: self.looks.append(look))
        patcher.start()
        self.addCleanup(patcher.stop)

    def look(self):
        while self.looks:
            update.refresh(*self.looks.pop(0))

    def welcome(self, now=NOW):
        """A start once the day's look, if one was due, has landed."""
        self.start(now)
        self.look()
        return self.start(now)

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
        update.refresh(self.copy, self.home, time.time())  # today's look has landed
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
        with mock.patch("afc.update.offer", side_effect=RuntimeError("boom")):
            self.assertEqual(self.message(), FIRST_RUN)

    def test_a_check_with_an_odd_answer_never_breaks_the_welcome(self):
        for answer in (None, [], "available", {"update": "available"}, {"update": "available", "latest": 5}):
            with self.subTest(answer=answer), mock.patch("afc.update.offer", return_value=answer):
                self.assertEqual(self.message(), FIRST_RUN)

    def test_an_unreadable_registry_is_not_held_up_by_a_check(self):
        self.tag("v0.02a")
        (self.home / "projects.json").write_text("{")
        with mock.patch("afc.update.offer") as offer:
            out = self.start()
        self.assertEqual(out["systemMessage"], BANNER)
        offer.assert_not_called()

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
        with mock.patch("afc.update.offer") as offer:
            message = self.message()
        offer.assert_not_called()
        self.assertEqual(self.looks, [])
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

    def test_a_start_that_begins_the_look_runs_no_git_and_goes_straight_ahead(self):
        self.tag("v0.02a")
        with mock.patch("afc.update.subprocess.run", side_effect=AssertionError("git ran in the welcome")):
            out = self.start()
        self.assertEqual(out["systemMessage"], FIRST_RUN)
        self.assertEqual(self.looks, [(self.copy, self.home, NOW)])

    def test_the_release_is_offered_from_the_start_after_the_look_has_landed(self):
        self.tag("v0.02a")
        self.assertEqual(self.start()["systemMessage"], FIRST_RUN)
        self.assertEqual(self.start(now=NOW + 5)["systemMessage"], FIRST_RUN)  # the look is still running
        self.look()
        self.assertEqual(self.start(now=NOW + 10)["systemMessage"], OFFER)

    def test_a_slow_look_is_not_begun_again_on_every_start(self):
        for now in (NOW, NOW + 60, NOW + 3600):
            self.start(now=now)
        self.assertEqual(len(self.looks), 1)
        self.start(now=NOW + DAY + 60)
        self.assertEqual(len(self.looks), 2)

    def test_yesterdays_answer_is_not_offered_while_todays_look_runs(self):
        self.tag("v0.02a")
        self.assertEqual(self.message(), OFFER)
        self.assertEqual(self.start(now=NOW + DAY + 60)["systemMessage"], FIRST_RUN)
        self.look()
        self.assertEqual(self.start(now=NOW + DAY + 120)["systemMessage"], OFFER)

    def test_a_workspace_that_cannot_be_written_does_not_begin_a_look_on_every_start(self):
        with mock.patch.object(update, "_save", return_value=False):
            self.start()
            self.start(now=NOW + 60)
        self.assertEqual(self.looks, [])

    def test_a_developer_copy_begins_no_look(self):
        git(self.copy, "switch", "-qc", "dev")
        self.start()
        self.assertEqual(self.looks, [])

    def test_the_look_is_its_own_process_and_the_next_start_offers_what_it_found(self):
        self.tag("v0.02a")
        started = []

        def real(*look):
            started.append(self.real_start_refresh(*look))
            return started[-1]

        with mock.patch.object(update, "start_refresh", side_effect=real):
            self.assertEqual(self.start()["systemMessage"], FIRST_RUN)
        self.addCleanup(lambda: [p.wait() for p in started if p])
        self.assertTrue(started[0], "the look did not start")
        self.assertEqual(started[0].wait(timeout=30), 0)
        self.assertEqual(self.start(now=NOW + 5)["systemMessage"], OFFER)


class WelcomeTimingTest(WelcomeCase):
    """FC-011 slice 3: the check never delays the welcome, however badly the remote or git behaves.
    These run the real background look; whatever it has not finished when the test ends is stopped."""

    def setUp(self):
        super().setUp()
        self.started = []
        real_popen = subprocess.Popen

        def watch(*args, **kwargs):
            self.started.append(real_popen(*args, **kwargs))
            return self.started[-1]

        for patcher in (mock.patch("afc.update.subprocess.Popen", side_effect=watch),
                        mock.patch.object(update, "start_refresh", self.real_start_refresh)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        for proc in self.started:  # before the folders go, so nothing recreates them
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        super().tearDown()

    def silent_origin(self):
        silent = socket.socket()
        silent.bind(("127.0.0.1", 0))
        silent.listen(5)
        self.addCleanup(silent.close)
        git(self.copy, "remote", "set-url", "origin", f"http://127.0.0.1:{silent.getsockname()[1]}/a.git")

    def hung_branch_lookup(self):
        real_run = subprocess.run

        def run(cmd, *args, **kwargs):
            if "rev-parse" not in cmd:
                return real_run(cmd, *args, **kwargs)
            time.sleep(kwargs["timeout"])
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

        patcher = mock.patch("afc.update.subprocess.run", side_effect=run)
        patcher.start()
        self.addCleanup(patcher.stop)

    def seconds_to_start(self):
        started = time.monotonic()
        out = self.start()
        self.assertEqual(out["systemMessage"], FIRST_RUN)
        return time.monotonic() - started

    def test_a_remote_that_never_answers_does_not_hold_up_the_welcome(self):
        self.silent_origin()
        took = self.seconds_to_start()
        self.assertLess(took, 1, f"the welcome waited {took:.1f}s for a silent remote")

    def test_a_hung_branch_lookup_and_a_remote_that_never_answers_do_not_hold_up_the_welcome(self):
        self.silent_origin()
        self.hung_branch_lookup()
        took = self.seconds_to_start()
        self.assertLess(took, 1, f"the welcome waited {took:.1f}s for a hung git and a silent remote")
