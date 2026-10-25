"""Tests for Flight Control's own version: the VERSION file, version order and `afc version`."""

from unittest.mock import patch

from afc import cli
from afc.version import Version, VersionError, parse, read
from tests.helpers import AfcTestCase, run_cli


class VersionFileTest(AfcTestCase):
    def test_the_version_file_is_read(self):
        (self.tmp / "VERSION").write_text("0.02a\n", encoding="utf-8")
        found = read(self.tmp)
        self.assertEqual(found, Version(0, 2, "a"))
        self.assertEqual(str(found), "0.02a")
        self.assertEqual(found.label(), "v0.02a")

    def test_a_missing_version_file_is_refused_in_plain_words(self):
        with self.assertRaises(VersionError) as caught:
            read(self.tmp)
        self.assertIn("VERSION", str(caught.exception))

    def test_a_version_file_that_is_not_a_version_is_refused(self):
        (self.tmp / "VERSION").write_text("banana\n", encoding="utf-8")
        with self.assertRaises(VersionError):
            read(self.tmp)


class VersionOrderTest(AfcTestCase):
    def test_minor_numbers_compare_as_numbers(self):
        self.assertLess(parse("0.01a"), parse("0.02a"))
        self.assertLess(parse("0.02a"), parse("0.10a"))

    def test_letters_come_after_the_bare_version(self):
        self.assertLess(parse("0.01"), parse("0.01a"))
        self.assertLess(parse("0.01a"), parse("0.01b"))
        self.assertLess(parse("0.01z"), parse("0.02"))

    def test_major_comes_first(self):
        self.assertLess(parse("0.99z"), parse("1.00a"))

    def test_a_list_sorts_into_release_order(self):
        shuffled = ["0.10a", "0.01b", "0.02a", "0.01a"]
        ordered = sorted(parse(text) for text in shuffled)
        self.assertEqual([str(v) for v in ordered], ["0.01a", "0.01b", "0.02a", "0.10a"])

    def test_the_v_prefix_is_optional_and_spaces_are_ignored(self):
        self.assertEqual(parse("v0.02a"), parse("0.02a"))
        self.assertEqual(parse(" 0.02a\n"), Version(0, 2, "a"))

    def test_text_that_is_not_a_version_is_refused(self):
        for text in ["", "banana", "1", "0.02ab", "0.02A", "0.a", "0.02a.1"]:
            with self.subTest(text=text), self.assertRaises(VersionError):
                parse(text)


class VersionCommandTest(AfcTestCase):
    def test_version_is_a_registered_command(self):
        self.assertIn("version", cli.COMMAND_NAMES)

    def test_version_prints_one_object_with_a_v_prefix(self):
        (self.tmp / "VERSION").write_text("0.02a\n", encoding="utf-8")
        with patch("afc.cli_update.afc_root", return_value=self.tmp):
            rc, out = run_cli(["version"])
        self.assertEqual((rc, out), (0, {"version": "v0.02a"}))

    def test_version_follows_the_file_it_reads(self):
        (self.tmp / "VERSION").write_text("0.10a\n", encoding="utf-8")
        with patch("afc.cli_update.afc_root", return_value=self.tmp):
            rc, out = run_cli(["version"])
        self.assertEqual((rc, out), (0, {"version": "v0.10a"}))

    def test_version_prints_the_version_of_this_copy(self):
        rc, out = run_cli(["version"])
        self.assertEqual((rc, out), (0, {"version": "v0.02a"}))

    def test_version_without_a_version_file_says_so_in_plain_words(self):
        with patch("afc.cli_update.afc_root", return_value=self.tmp):
            rc, out = run_cli(["version"])
        self.assertEqual(rc, 1)
        self.assertIn("VERSION", out["error"])
