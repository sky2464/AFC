"""Tests for FC-011 slice 2: checking for a newer release (update --check)."""

import json
import os
import subprocess
from pathlib import Path
from unittest import mock

from afc import update
from afc.config import set_maintain
from tests.helpers import AfcTestCase, run_cli

DAY = 86400


def git(cwd, *args):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main", *args],
        cwd=cwd, check=True, capture_output=True, env=env,
    )


class UpdateCheckTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.remote = self.tmp / "remote"
        self.remote.mkdir()
        git(self.remote, "init", "-q")
        (self.remote / "VERSION").write_text("v0.01a\n")
        git(self.remote, "add", "VERSION")
        git(self.remote, "commit", "-qm", "one")
        git(self.remote, "tag", "v0.01a")
        self.copy = self.tmp / "copy"
        git(self.tmp, "clone", "-q", str(self.remote), str(self.copy))

    def tag(self, *names):
        for name in names:
            git(self.remote, "tag", name)

    def check(self, now=1_000_000.0):
        return update.check(self.copy, self.home, now=now)

    def test_newer_tag_is_offered(self):
        self.tag("v0.02a")
        self.assertEqual(self.check(), {"update": "available", "current": "v0.01a", "latest": "v0.02a"})

    def test_version_order_not_text_or_date(self):
        self.tag("v0.10a", "v0.09a")
        self.assertEqual(self.check()["latest"], "v0.10a")

    def test_only_v_tags_count(self):
        self.tag("release-9", "v9-beta", "nightly")
        self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})

    def test_no_newer_tag(self):
        self.assertEqual(self.check()["update"], "none")

    def test_offline_says_nothing(self):
        git(self.copy, "remote", "set-url", "origin", str(self.tmp / "gone"))
        self.assertEqual(self.check(), {"update": "none", "current": "v0.01a"})

    def test_short_timeout_counts_as_offline(self):
        def slow(*a, **k):
            raise subprocess.TimeoutExpired(a[0], k.get("timeout"))

        with mock.patch("afc.update.subprocess.run", side_effect=slow) as run:
            self.assertEqual(self.check()["update"], "none")
        self.assertLessEqual(run.call_args.kwargs["timeout"], update.TIMEOUT)
        self.assertLessEqual(update.TIMEOUT, 5)

    def test_runs_at_most_once_a_day(self):
        self.check(now=1_000_000.0)
        self.tag("v0.02a")
        self.assertEqual(self.check(now=1_000_000.0 + DAY - 60)["update"], "none")
        self.assertEqual(self.check(now=1_000_000.0 + DAY + 60)["latest"], "v0.02a")

    def test_cached_result_is_reused(self):
        self.tag("v0.02a")
        self.check()
        stored = json.loads((self.home / update.STATE).read_text())
        self.assertEqual(stored["latest"], "v0.02a")
        git(self.copy, "remote", "set-url", "origin", str(self.tmp / "gone"))
        self.assertEqual(self.check(now=1_000_100.0)["latest"], "v0.02a")

    def test_skipped_release_stays_quiet(self):
        self.tag("v0.02a")
        update.skip(self.home, "v0.02a")
        self.assertEqual(self.check()["update"], "none")
        self.tag("v0.03a")
        self.assertEqual(self.check(now=1_000_000.0 + 2 * DAY)["latest"], "v0.03a")

    def test_developer_copy_on_dev_never_offers(self):
        self.tag("v0.02a")
        git(self.copy, "switch", "-qc", "dev")
        self.assertEqual(self.check()["update"], "none")

    def test_maintenance_mode_never_offers(self):
        self.tag("v0.02a")
        set_maintain(self.home, True)
        self.assertEqual(self.check()["update"], "none")


class UpdateCommandTest(UpdateCheckTest):
    def test_command_prints_one_object(self):
        self.tag("v0.02a")
        with mock.patch("afc.cli_version.afc_root", return_value=self.copy):
            code, out = run_cli(["update", "--check"])
        self.assertEqual((code, out["update"], out["latest"]), (0, "available", "v0.02a"))

    def test_command_skip(self):
        self.tag("v0.02a")
        with mock.patch("afc.cli_version.afc_root", return_value=self.copy):
            code, out = run_cli(["update", "--skip", "v0.02a"])
            self.assertEqual((code, out), (0, {"skipped": "v0.02a"}))
            code, out = run_cli(["update", "--check"])
        self.assertEqual(out["update"], "none")

    def test_bad_skip_is_an_error(self):
        code, out = run_cli(["update", "--skip", "banana"])
        self.assertNotEqual(code, 0)
        self.assertIn("error", out)


if __name__ == "__main__":
    import unittest

    unittest.main()
