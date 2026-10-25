"""Tests for FC-026 slice 2: release check."""

import subprocess
from unittest import mock

from afc import release
from tests.helpers import AfcTestCase, run_cli


class ReleaseCheckTest(AfcTestCase):
    def git(self, *args, env=None):
        return subprocess.run(["git", "-C", str(self.tmp), "-c", "user.name=t", "-c", "user.email=t@t",
                               *args], check=True, capture_output=True, text=True).stdout

    def commit(self, msg, date="2026-01-01T12:00:00"):
        self.git("add", "-A")
        subprocess.run(["git", "-C", str(self.tmp), "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "-m", msg, "--date", date], check=True, capture_output=True,
                       env={**__import__("os").environ, "GIT_COMMITTER_DATE": date})

    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        (self.tmp / "docs").mkdir()
        (self.tmp / "VERSION").write_text("v0.02a\n", encoding="utf-8")
        (self.tmp / "docs" / "changelog.md").write_text("# Changelog\n\n## 2026-01-01 — old\n", encoding="utf-8")
        self.commit("release")
        self.git("tag", "v0.02a")
        # a ready state: bumped version, new changelog heading, clean tree
        (self.tmp / "VERSION").write_text("v0.03a\n", encoding="utf-8")
        (self.tmp / "docs" / "changelog.md").write_text(
            "# Changelog\n\n## 2026-02-01 — new\n\n## 2026-01-01 — old\n", encoding="utf-8")
        self.commit("next", "2026-02-01T12:00:00")

    def problems(self):
        return release.check(self.tmp)["problems"]

    def test_all_clear(self):
        self.assertEqual(release.check(self.tmp), {"ready": True, "problems": []})

    def test_not_on_main(self):
        self.git("switch", "-q", "-c", "dev")
        out = release.check(self.tmp)
        self.assertFalse(out["ready"])
        self.assertEqual(len(out["problems"]), 1)
        self.assertIn("not on main", out["problems"][0])

    def test_uncommitted_changes(self):
        (self.tmp / "x.txt").write_text("x", encoding="utf-8")
        p = self.problems()
        self.assertEqual(len(p), 1)
        self.assertIn("uncommitted", p[0])

    def test_version_not_newer(self):
        (self.tmp / "VERSION").write_text("v0.02a\n", encoding="utf-8")
        self.commit("same")
        p = self.problems()
        self.assertTrue(any("not newer" in x for x in p))
        self.assertNotIn("uncommitted", " ".join(p))

    def test_no_changelog_entry(self):
        (self.tmp / "docs" / "changelog.md").write_text("# Changelog\n\n## 2026-01-01 — old\n", encoding="utf-8")
        self.commit("no entry", "2026-02-02T12:00:00")
        p = self.problems()
        self.assertEqual(len(p), 1)
        self.assertIn("changelog", p[0])

    def test_version_heading_counts(self):
        (self.tmp / "docs" / "changelog.md").write_text("# Changelog\n\n## v0.03a\n\n## 2026-01-01 — old\n",
                                                        encoding="utf-8")
        self.commit("named", "2026-02-02T12:00:00")
        self.assertEqual(self.problems(), [])

    def test_tag_already_exists(self):
        self.git("tag", "v0.03a", "HEAD")
        self.git("switch", "-q", "-c", "side", "HEAD~1")
        self.git("switch", "-q", "main")
        # make the tag unreachable from main so only the tag problem shows
        self.git("tag", "-d", "v0.03a")
        self.git("switch", "-q", "side")
        (self.tmp / "s").write_text("s", encoding="utf-8")
        self.commit("side")
        self.git("tag", "v0.03a")
        self.git("switch", "-q", "main")
        p = self.problems()
        self.assertEqual(len(p), 1)
        self.assertIn("already exists", p[0])

    def test_changes_nothing(self):
        (self.tmp / "x.txt").write_text("x", encoding="utf-8")
        before = self.git("status", "--short")
        refs = self.git("for-each-ref")
        release.check(self.tmp)
        self.assertEqual(self.git("status", "--short"), before)
        self.assertEqual(self.git("for-each-ref"), refs)

    def test_command(self):
        with mock.patch("afc.cli_version.afc_root", return_value=self.tmp):
            code, out = run_cli(["release", "check"])
        self.assertEqual((code, out["ready"]), (0, True))
