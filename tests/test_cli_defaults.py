"""Tests for `sh bin/afc defaults`: what Flight Control can work out before asking."""

import subprocess
import unittest
from pathlib import Path
from unittest import mock

from afc.registry import Project, load_registry, save_registry
from tests.helpers import AfcTestCase, run_cli


def git_config_says(name: str = "", email: str = ""):
    """A stand-in for subprocess.run that answers `git config --global user.name|email`."""
    answers = {"user.name": name, "user.email": email}

    def run(cmd, **kwargs):
        value = answers.get(cmd[-1], "")
        return subprocess.CompletedProcess(cmd, 0 if value else 1, stdout=value + "\n" if value else "")

    return run


class DefaultsTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.user_home = self.tmp / "me"
        self.user_home.mkdir()
        patch = mock.patch("pathlib.Path.home", return_value=self.user_home)
        patch.start()
        self.addCleanup(patch.stop)
        self.synced: set[Path] = set()
        patch = mock.patch("afc.cli.icloud_synced", side_effect=lambda p: Path(p) in self.synced)
        patch.start()
        self.addCleanup(patch.stop)

    def defaults(self, git=None):
        with mock.patch("afc.cli_defaults.subprocess.run", git or git_config_says()):
            code, out = run_cli(["defaults"])
        self.assertEqual(code, 0, out)
        return out

    def add_project(self, name, git_name, git_email, last_active):
        reg = load_registry(self.home)
        reg.add(Project(name=name, code_path=str(self.tmp / name), workspace_path=str(self.tmp / "ws" / name),
                        git_name=git_name, git_email=git_email, last_active=last_active))
        save_registry(self.home, reg)

    # ---- the parent folder

    def test_first_existing_folder_in_order(self):
        (self.user_home / "Projects").mkdir()
        (self.user_home / "Developer").mkdir()
        self.assertEqual(self.defaults()["parent"], str(self.user_home / "Developer"))

    def test_code_comes_first(self):
        for name in ("Code", "Developer", "Projects"):
            (self.user_home / name).mkdir()
        self.assertEqual(self.defaults()["parent"], str(self.user_home / "Code"))

    def test_icloud_folders_are_skipped(self):
        (self.user_home / "Code").mkdir()
        (self.user_home / "Projects").mkdir()
        self.synced.add(self.user_home / "Code")
        self.assertEqual(self.defaults()["parent"], str(self.user_home / "Projects"))

    def test_nothing_found_proposes_creating_code(self):
        out = self.defaults()
        self.assertIsNone(out["parent"])
        self.assertEqual(out["suggest_create"], str(self.user_home / "Code"))

    def test_nothing_found_and_code_synced_proposes_nothing(self):
        self.synced.add(self.user_home / "Code")
        out = self.defaults()
        self.assertIsNone(out["parent"])
        self.assertIsNone(out["suggest_create"])

    def test_a_file_named_code_is_not_a_folder(self):
        (self.user_home / "Code").write_text("not a folder")
        self.assertIsNone(self.defaults()["parent"])

    def test_found_parent_has_no_suggestion(self):
        (self.user_home / "Code").mkdir()
        self.assertIsNone(self.defaults()["suggest_create"])

    # ---- the git identity

    def test_identity_from_the_most_recent_project(self):
        self.add_project("older", "Old Name", "old@example.com", "2026-10-01")
        self.add_project("newer", "Navid", "navid@example.com", "2026-10-20")
        out = self.defaults(git_config_says("Global", "global@example.com"))
        self.assertEqual((out["git_name"], out["git_email"], out["source"]),
                         ("Navid", "navid@example.com", "projects"))

    def test_projects_without_an_identity_are_ignored(self):
        self.add_project("blank", "", "", "2026-10-20")
        self.add_project("real", "Navid", "navid@example.com", "2026-10-01")
        self.assertEqual(self.defaults()["git_name"], "Navid")

    def test_identity_from_git_config_when_no_project_has_one(self):
        out = self.defaults(git_config_says("Global", "global@example.com"))
        self.assertEqual((out["git_name"], out["git_email"], out["source"]),
                         ("Global", "global@example.com", "git-config"))

    def test_half_an_identity_is_not_used(self):
        out = self.defaults(git_config_says("Global", ""))
        self.assertEqual((out["git_name"], out["git_email"], out["source"]), ("", "", "none"))

    def test_nothing_found(self):
        out = self.defaults()
        self.assertEqual((out["git_name"], out["git_email"], out["source"]), ("", "", "none"))

    def test_git_missing_is_not_an_error(self):
        with mock.patch("afc.cli_defaults.subprocess.run", side_effect=FileNotFoundError):
            code, out = run_cli(["defaults"])
        self.assertEqual((code, out["source"]), (0, "none"))

    # ---- the rest

    def test_ai_trailer_is_off(self):
        self.assertIs(self.defaults()["ai_trailer"], False)

    def test_changes_nothing(self):
        before = sorted(p.name for p in self.user_home.iterdir())
        self.defaults()
        self.assertEqual(sorted(p.name for p in self.user_home.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
