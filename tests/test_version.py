"""Tests for FC-011 slice 1: Flight Control knows its version (VERSION file, ordering, command)."""

import unittest
from unittest import mock

from afc import version
from afc.config import afc_root
from tests.helpers import AfcTestCase, run_cli


class ReadVersionTest(AfcTestCase):
    def test_reads_the_version_file(self):
        (self.tmp / "VERSION").write_text("v0.02a\n", encoding="utf-8")
        self.assertEqual(version.installed(self.tmp), "v0.02a")

    def test_missing_file_is_an_error(self):
        with self.assertRaises(version.VersionError):
            version.installed(self.tmp)

    def test_bad_contents_are_an_error(self):
        (self.tmp / "VERSION").write_text("banana\n", encoding="utf-8")
        with self.assertRaises(version.VersionError):
            version.installed(self.tmp)

    def test_repo_has_a_valid_version_file(self):
        self.assertTrue(version.is_version(version.installed(afc_root())))


class OrderingTest(unittest.TestCase):
    def test_numeric_not_text_order(self):
        self.assertLess(version.key("v0.01a"), version.key("v0.02a"))
        self.assertLess(version.key("v0.02a"), version.key("v0.10a"))
        self.assertLess(version.key("v0.09a"), version.key("v0.10a"))
        self.assertLess(version.key("v0.99a"), version.key("v1.00a"))

    def test_unpadded_numbers_are_not_compared_as_text(self):
        # as text "v0.10a" < "v0.9a" and "v10.0a" < "v9.0a"
        self.assertLess(version.key("v0.9a"), version.key("v0.10a"))
        self.assertLess(version.key("v9.0a"), version.key("v10.0a"))
        self.assertLess(version.key("v1.2.9a"), version.key("v1.2.10a"))
        self.assertLess(version.key("v0.9z"), version.key("v0.10a"))

    def test_letter_breaks_ties(self):
        self.assertLess(version.key("v0.01a"), version.key("v0.01b"))

    def test_newest(self):
        self.assertEqual(version.newest(["v0.10a", "v0.02a", "junk", "v0.09a"]), "v0.10a")
        self.assertIsNone(version.newest(["junk"]))

    def test_newest_is_numeric_not_text(self):
        self.assertEqual(version.newest(["v0.9a", "v0.10a", "v9.0a", "v10.0a"]), "v10.0a")
        self.assertEqual(version.newest(["v0.9a", "v0.10a"]), "v0.10a")

    def test_is_newer(self):
        self.assertTrue(version.is_newer("v0.10a", "v0.02a"))
        self.assertFalse(version.is_newer("v0.02a", "v0.02a"))

    def test_is_newer_is_numeric_not_text(self):
        self.assertTrue(version.is_newer("v0.10a", "v0.9a"))
        self.assertFalse(version.is_newer("v0.9a", "v0.10a"))
        self.assertTrue(version.is_newer("v10.0a", "v9.0a"))
        self.assertFalse(version.is_newer("v9.0a", "v10.0a"))

    def test_rejects_non_versions(self):
        for bad in ("0.01a", "v1", "va.b", "", "v0.01a-dev"):
            self.assertFalse(version.is_version(bad), bad)
            with self.assertRaises(version.VersionError):
                version.key(bad)


    def test_things_that_are_not_text_are_not_versions(self):
        for bad in (5, 1.5, True, None, ["v0.01a"], {"a": 1}, b"v0.01a"):
            self.assertFalse(version.is_version(bad), bad)
            with self.assertRaises(version.VersionError):
                version.key(bad)


class VersionCommandTest(AfcTestCase):
    def test_prints_installed_version(self):
        (self.tmp / "VERSION").write_text("v0.01a\n", encoding="utf-8")
        with mock.patch("afc.cli_version.afc_root", return_value=self.tmp):
            code, out = run_cli(["version"])
        self.assertEqual((code, out), (0, {"version": "v0.01a"}))

    def test_missing_file_reports_an_error(self):
        with mock.patch("afc.cli_version.afc_root", return_value=self.tmp):
            code, out = run_cli(["version"])
        self.assertNotEqual(code, 0)
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()


class NotBehindReleaseTest(AfcTestCase):
    """FC-026 slice 1: VERSION is never older than the newest v* tag merged into main."""

    def _repo(self, tags):
        import subprocess

        def git(*args):
            subprocess.run(["git", "-C", str(self.tmp), "-c", "user.name=t", "-c", "user.email=t@t",
                            *args], check=True, capture_output=True)

        git("init", "-q", "-b", "main")
        (self.tmp / "f").write_text("x", encoding="utf-8")
        git("add", "f")
        git("commit", "-q", "-m", "one")
        for tag in tags:
            git("tag", tag)
        return self.tmp

    def test_equal_passes(self):
        self.assertIsNone(version.behind_release("v0.02a", self._repo(["v0.01a", "v0.02a"])))

    def test_newer_passes(self):
        self.assertIsNone(version.behind_release("v0.03a", self._repo(["v0.02a"])))

    def test_older_fails(self):
        problem = version.behind_release("v0.01a", self._repo(["v0.01a", "v0.02a"]))
        self.assertIn("v0.02a", problem)

    def test_no_tags_passes(self):
        self.assertIsNone(version.behind_release("v0.01a", self._repo([])))

    def test_this_repo_is_not_behind(self):
        root = afc_root()
        problem = version.behind_release(version.installed(root), root)
        self.assertIsNone(problem, problem)
