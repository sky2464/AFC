"""Tests for the slice review: checks, verdict, report and the review command.

The external scanners are stubbed the same way tests/test_scan.py stubs them, so these tests
need no network and no installed tools.
"""

import json
import subprocess
from pathlib import Path
from unittest import mock

from afc import review
from afc.registry import Project, Registry, save_registry
from afc.scan import Check, run_checks, write_report
from tests.helpers import AfcTestCase, fixture, run_cli


def _git_repo(path: Path, files: dict[str, str]) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    for name, text in files.items():
        (path / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    return path


def _installed(*names: str):
    """Pretend only these tools are on PATH."""
    return mock.patch("afc.scan.shutil.which", side_effect=lambda n: f"/x/{n}" if n in names else None)


def _scanner_output(outputs: dict[str, str]):
    """Stub the external scanners: each installed command prints its text, none is run."""
    def run(cmd, cwd):
        return subprocess.CompletedProcess(cmd, 0, stdout=outputs.get(cmd[0], ""), stderr="")
    return mock.patch("afc.scan._run_tool", side_effect=run)


def _files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*")
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def _sidecar(report: str) -> dict:
    return json.loads(Path(report).with_suffix(".json").read_text(encoding="utf-8"))


class ReviewVerdictTests(AfcTestCase):
    def test_clean_project_is_ok_and_missing_tools_count_as_neither(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "print(1)\n"})
        with mock.patch("afc.scan.shutil.which", return_value=None):
            result = review.run_review(repo, self.tmp / "ws", "1 Login")
        self.assertEqual(result["verdict"], "ok")
        self.assertEqual((result["critical"], result["warning"]), (0, 0))

    def test_failed_builtin_check_blocks(self):
        secret = "AKIA" + "ABCDEFGHIJKLMNOP"
        repo = _git_repo(self.tmp / "app", {"config.py": f"KEY = '{secret}'\n"})
        with mock.patch("afc.scan.shutil.which", return_value=None):
            result = review.run_review(repo, self.tmp / "ws", "1 Login")
        self.assertEqual(result["verdict"], "blocked")
        self.assertEqual((result["critical"], result["warning"]), (1, 0))

    def test_failed_scanner_blocks(self):
        repo = _git_repo(self.tmp / "app", {"package.json": "{}\n"})
        with _installed("npm"), _scanner_output({"npm": fixture("npm-audit-2high.json")}):
            result = review.run_review(repo, self.tmp / "ws", "1 Login")
        self.assertEqual(result["verdict"], "blocked")
        self.assertEqual(result["critical"], 1)

    def test_warning_is_counted_but_does_not_block(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "print(1)\n"})
        with _installed("semgrep"), _scanner_output({"semgrep": '{"results": [{"check_id": "x"}]}'}):
            result = review.run_review(repo, self.tmp / "ws", "1 Login")
        self.assertEqual(result["verdict"], "ok")
        self.assertEqual((result["critical"], result["warning"]), (0, 1))


SPEC = """# S-001 Login

## You'll know it works when

- When a user logs in with a wrong password, then an error message is shown.
- When the session expires, then the user is sent back to the login page.

## Slices
"""


def _planned(ws: Path) -> None:
    (ws / "plan" / "specs").mkdir(parents=True)
    (ws / "plan" / "specs" / "S-001-login.md").write_text(SPEC, encoding="utf-8")
    (ws / "plan" / "master-plan.md").write_text(
        "## Now\n\n| ID | Title | Size | Spec | Started |\n|---|---|---|---|---|\n"
        "| S-001 | Login | S | [spec](specs/S-001-login.md) | 2026-10-25 |\n\n## Next\n",
        encoding="utf-8")


class ReviewOwnChecksTests(AfcTestCase):
    def _review(self, files, planned=True):
        repo = _git_repo(self.tmp / "app", files)
        ws = self.tmp / "ws"
        if planned:
            _planned(ws)
        with mock.patch("afc.scan.shutil.which", return_value=None):
            result = review.run_review(repo, ws, "1 Login")
        return result, Path(result["report"]).read_text(encoding="utf-8")

    def test_501_line_file_blocks_and_is_named(self):
        result, text = self._review({"big.py": "x = 1\n" * 501}, planned=False)
        self.assertEqual((result["verdict"], result["critical"]), ("blocked", 1))
        self.assertIn("big.py", text)

    def test_500_line_file_is_fine(self):
        result, _ = self._review({"big.py": "x = 1\n" * 500}, planned=False)
        self.assertEqual(result["verdict"], "ok")

    def test_untested_line_blocks_and_is_quoted_in_full(self):
        tests = "def test_user_logs_in_wrong_password_error_message_shown(): pass\n"
        result, text = self._review({"test_login.py": tests})
        self.assertEqual((result["verdict"], result["critical"]), ("blocked", 1))
        self.assertIn("When the session expires, then the user is sent back to the login page.", text)
        self.assertNotIn("wrong password, then", text)

    def test_every_line_tested_stays_ok(self):
        tests = ("def test_user_logs_in_wrong_password_error_message_shown(): pass\n"
                 "def test_expired_session_sends_the_user_back_to_the_login_page(): pass\n")
        result, _ = self._review({"test_login.py": tests})
        self.assertEqual((result["verdict"], result["critical"]), ("ok", 0))


class ReviewRegressionTests(AfcTestCase):
    def _review(self, label, files, extra=None):
        repo = _git_repo(self.tmp / "app", {"app.py": "print(1)\n"})
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"],
                       cwd=repo, check=True)
        for name, text in files.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text, encoding="utf-8")
        with mock.patch("afc.scan.shutil.which", return_value=None):
            result = review.run_review(repo, self.tmp / "ws", label)
        return result, Path(result["report"]).read_text(encoding="utf-8")

    def test_bug_fix_without_regression_test_is_blocked(self):
        result, text = self._review("2 Fix login crash", {"app.py": "print(2)\n"})
        self.assertEqual((result["verdict"], result["critical"]), ("blocked", 1))
        self.assertIn("regression test", text)

    def test_bug_fix_passes_once_the_regression_test_exists(self):
        files = {"app.py": "print(2)\n",
                 "tests/test_login.py": "def test_regression_login_crash(): pass\n"}
        result, _ = self._review("2 Fix login crash", files)
        self.assertEqual((result["verdict"], result["critical"]), ("ok", 0))

    def test_a_test_that_is_not_named_regression_does_not_count(self):
        files = {"app.py": "print(2)\n", "tests/test_login.py": "def test_login(): pass\n"}
        result, _ = self._review("2 Fix login crash", files)
        self.assertEqual(result["verdict"], "blocked")

    def test_a_feature_slice_needs_no_regression_test(self):
        result, _ = self._review("2 Add logout", {"app.py": "print(2)\n"})
        self.assertEqual(result["verdict"], "ok")


class ReviewReportTests(AfcTestCase):
    def test_report_written_beside_scan_reports(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "print(1)\n"})
        ws = self.tmp / "ws"
        before = _files(repo)
        with mock.patch("afc.scan.shutil.which", return_value=None):
            result = review.run_review(repo, ws, "1 Login")
        report = Path(result["report"])
        self.assertTrue(report.is_relative_to(ws / "reports"))
        self.assertTrue(report.exists())
        self.assertIn("Verdict: ok", report.read_text(encoding="utf-8"))
        sidecar = _sidecar(result["report"])
        self.assertEqual((sidecar["label"], sidecar["verdict"]), ("1 Login", "ok"))
        self.assertEqual(_files(repo), before)

    def test_existing_scan_checks_are_included(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "print(1)\n", "package.json": "{}\n",
                                            "requirements.txt": "x\n"})
        outputs = {"npm": fixture("npm-audit-clean.json"), "pip-audit": '{"dependencies": []}'}
        with _installed("npm", "pip-audit"), _scanner_output(outputs):
            expected = [c.name for c in run_checks(repo)]
            result = review.run_review(repo, self.tmp / "ws", "1 Login")
        self.assertEqual([c["name"] for c in _sidecar(result["report"])["checks"]], expected)
        for name in ("secrets", "npm audit", "pip-audit", "gitleaks", "semgrep"):
            self.assertIn(name, expected)

    def test_write_report_shows_verdict_when_given(self):
        path = write_report(self.tmp / "ws", [Check("secrets", "fail", "secrets in 1 file(s)")],
                            "1 Login", verdict="blocked")
        self.assertIn("Verdict: blocked", path.read_text(encoding="utf-8"))
        self.assertEqual(_sidecar(str(path))["verdict"], "blocked")

    def test_write_report_without_verdict_is_unchanged(self):
        path = write_report(self.tmp / "ws", [Check("secrets", "pass", "no secrets")], "Login")
        self.assertNotIn("Verdict", path.read_text(encoding="utf-8"))
        self.assertNotIn("verdict", _sidecar(str(path)))


class ReviewCommandTests(AfcTestCase):
    def _activate(self, repo: Path, ws: Path) -> None:
        reg = Registry()
        reg.add(Project(name="app", code_path=str(repo), workspace_path=str(ws)))
        reg.set_active("app")
        save_registry(self.home, reg)

    def test_review_is_a_command(self):
        from afc import cli

        self.assertIn("review", cli.COMMAND_NAMES)

    def test_no_active_project(self):
        code, out = run_cli(["review", "--slice", "1 Login"])
        self.assertEqual(code, 1)
        self.assertIn("type /afc", out["error"])

    def test_slice_is_required(self):
        code, out = run_cli(["review"])
        self.assertEqual(code, 1)
        self.assertIn("error", out)

    def test_prints_verdict_critical_warning_and_report(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "print(1)\n"})
        ws = self.tmp / "ws"
        ws.mkdir()
        self._activate(repo, ws)
        with mock.patch("afc.scan.shutil.which", return_value=None):
            code, out = run_cli(["review", "--slice", "1 Login"])
        self.assertEqual(code, 0)
        self.assertEqual(set(out), {"verdict", "critical", "warning", "report"})
        self.assertEqual((out["verdict"], out["critical"], out["warning"]), ("ok", 0, 0))
        self.assertTrue(Path(out["report"]).is_relative_to(ws / "reports"))

    def test_blocked_is_a_result_not_an_error(self):
        secret = "AKIA" + "ABCDEFGHIJKLMNOP"
        repo = _git_repo(self.tmp / "app", {"config.py": f"KEY = '{secret}'\n"})
        ws = self.tmp / "ws"
        ws.mkdir()
        self._activate(repo, ws)
        with mock.patch("afc.scan.shutil.which", return_value=None):
            code, out = run_cli(["review", "--slice", "1 Login"])
        self.assertEqual(code, 0)
        self.assertEqual((out["verdict"], out["critical"]), ("blocked", 1))
