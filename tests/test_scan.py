"""Tests for slice checks, summary line and report."""

import json
import os
import subprocess
from pathlib import Path
from unittest import mock

from afc.registry import Project, Registry, save_registry
from afc.scan import (
    Check,
    agent_files_scan,
    builtin_secret_scan,
    parse_bun_audit,
    parse_npm_audit,
    parse_pip_audit,
    pip_audit_command,
    run_checks,
    slug,
    summary_line,
    write_report,
)
from tests.helpers import AfcTestCase, fixture, run_cli


def _git_repo(path: Path, files: dict[str, str]) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    for name, text in files.items():
        (path / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    return path


class ScanTests(AfcTestCase):
    def test_summary_line_format(self):
        s = summary_line([Check("secrets", "pass", "no secrets"), Check("npm", "pass", "0 vulnerable deps"),
                          Check("semgrep", "warn", "/orders has no rate limit"), Check("gitleaks", "missing", "")])
        self.assertEqual(s, "✅ no secrets · ✅ 0 vulnerable deps · ⚠️ /orders has no rate limit · ⚪ gitleaks not installed")

    def test_summary_line_fail(self):
        self.assertEqual(summary_line([Check("secrets", "fail", "secrets in 1 file(s)")]), "❌ secrets in 1 file(s)")

    def test_npm_clean(self):
        c = parse_npm_audit(fixture("npm-audit-clean.json"))
        self.assertEqual((c.status, c.detail), ("pass", "0 vulnerable deps"))

    def test_npm_vulns(self):
        c = parse_npm_audit(fixture("npm-audit-2high.json"))
        self.assertEqual(c.status, "fail")
        self.assertIn("2 vulnerable deps", c.detail)
        self.assertEqual(c.detail, "2 vulnerable deps (2 high)")

    def test_bun_clean(self):
        c = parse_bun_audit(fixture("bun-audit-clean.json"))
        self.assertEqual((c.name, c.status, c.detail), ("bun audit", "pass", "0 vulnerable deps"))

    def test_bun_vulns(self):
        c = parse_bun_audit(fixture("bun-audit-2high.json"))
        self.assertEqual((c.status, c.detail), ("fail", "2 vulnerable deps (2 high)"))

    def test_bun_real_output_recorded_2026_10_24(self):
        """Real `bun audit --json` (Bun 1.3.14) for lodash 4.17.15; Bun prints its banner on stderr."""
        c = parse_bun_audit(fixture("bun-audit-real-lodash.json"))
        self.assertEqual((c.name, c.status), ("bun audit", "fail"))
        self.assertEqual(c.detail, "1 vulnerable deps (3 high)")

    def test_bun_unreadable(self):
        self.assertEqual(parse_bun_audit("not json").status, "warn")

    def test_bun_audit_used_for_bun_project(self):
        repo = _git_repo(self.tmp / "app", {"package.json": "{}\n", "bun.lock": "{}\n"})
        done = subprocess.CompletedProcess([], 1, stdout=fixture("bun-audit-2high.json"), stderr="")
        with mock.patch("afc.scan.shutil.which", side_effect=lambda n: "/x/bun" if n == "bun" else None), \
                mock.patch("afc.scan._run_tool", return_value=done) as run:
            checks = {c.name: c for c in run_checks(repo)}
        self.assertEqual(checks["bun audit"].status, "fail")
        self.assertNotIn("npm audit", checks)
        self.assertEqual(run.call_args[0][0], ["bun", "audit", "--json"])

    def test_npm_without_lockfile_says_so(self):
        repo = _git_repo(self.tmp / "app", {"package.json": "{}\n"})
        done = subprocess.CompletedProcess([], 1, stdout='{"error":{"code":"ENOLOCK"}}', stderr="")
        with mock.patch("afc.scan.shutil.which", side_effect=lambda n: "/x/npm" if n == "npm" else None), \
                mock.patch("afc.scan._run_tool", return_value=done):
            checks = {c.name: c for c in run_checks(repo)}
        self.assertEqual(checks["npm audit"].detail, "no lockfile, so dependencies were not audited")

    def test_pip_vulns(self):
        c = parse_pip_audit(fixture("pip-audit-1.json"))
        self.assertEqual((c.status, c.detail), ("fail", "1 vulnerable deps (0 high)"))

    def test_pip_clean(self):
        self.assertEqual(parse_pip_audit('{"dependencies":[]}').status, "pass")

    def test_builtin_scan_finds_committed_key(self):
        repo = _git_repo(self.tmp / "app", {"config.py": "KEY = '" + "AKIA" + "ABCDEFGHIJKLMNOP" + "'\n",
                                            "ok.py": "print(1)\n"})
        c = builtin_secret_scan(repo)
        self.assertEqual((c.status, c.detail), ("fail", "secrets in 1 file(s)"))

    def test_builtin_scan_clean_skips_binary_and_untracked(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "print(1)\n"})
        (repo / "bin.dat").write_bytes(b"\x00" + ("AKIA" + "ABCDEFGHIJKLMNOP").encode())
        subprocess.run(["git", "add", "bin.dat"], cwd=repo, check=True)
        (repo / "untracked.py").write_text("AKIA" + "ABCDEFGHIJKLMNOP", encoding="utf-8")
        self.assertEqual(builtin_secret_scan(repo).detail, "no secrets")

    def test_agent_files_untracked_agents_md_warns_by_name(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "x\n"})
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], cwd=repo, check=True)
        (repo / "AGENTS.md").write_text("Read the guide first.\n", encoding="utf-8")
        c = agent_files_scan(repo)
        self.assertEqual((c.name, c.status), ("agent files", "warn"))
        self.assertIn("AGENTS.md", c.detail)

    def test_agent_files_staged_and_nested_names(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "x\n"})
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], cwd=repo, check=True)
        (repo / ".github").mkdir()
        (repo / ".github" / "copilot-instructions.md").write_text("hi\n", encoding="utf-8")
        (repo / ".cursorrules").write_text("hi\n", encoding="utf-8")
        (repo / "sub").mkdir()
        (repo / "sub" / "CLAUDE.md").write_text("hi\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        detail = agent_files_scan(repo).detail
        for name in (".github/copilot-instructions.md", ".cursorrules", "sub/CLAUDE.md"):
            self.assertIn(name, detail)

    def test_agent_files_changed_since_last_commit(self):
        repo = _git_repo(self.tmp / "app", {"CLAUDE.md": "one\n", "ok.py": "x\n"})
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], cwd=repo, check=True)
        self.assertIsNone(agent_files_scan(repo))
        (repo / "CLAUDE.md").write_text("two\n", encoding="utf-8")
        self.assertIn("CLAUDE.md", agent_files_scan(repo).detail)

    def test_agent_files_none_or_not_a_repo_is_quiet(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "x\n", "notes.md": "x\n"})
        self.assertIsNone(agent_files_scan(repo))
        plain = self.tmp / "plain"
        plain.mkdir()
        self.assertIsNone(agent_files_scan(plain))

    def test_run_checks_includes_agent_files_only_when_found(self):
        repo = _git_repo(self.tmp / "app", {"AGENTS.md": "hi\n"})
        names = [c.name for c in run_checks(repo)]
        self.assertIn("agent files", names)
        repo2 = _git_repo(self.tmp / "app2", {"ok.py": "x\n"})
        self.assertNotIn("agent files", [c.name for c in run_checks(repo2)])

    def test_missing_tools_reported_not_skipped(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "x\n", "requirements.txt": "x\n"})
        git_dir = str(Path(subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()).parent)
        empty = self.tmp / "emptybin"
        empty.mkdir()
        (empty / "git").symlink_to(Path(git_dir) / "git")
        with mock.patch.dict(os.environ, {"PATH": str(empty)}):
            checks = {c.name: c for c in run_checks(repo)}
        self.assertEqual(checks["secrets"].status, "pass")
        self.assertEqual(checks["gitleaks"].status, "missing")
        self.assertEqual(checks["semgrep"].status, "missing")
        self.assertEqual(checks["pip-audit"].status, "missing")
        self.assertNotIn("npm audit", checks)

    def test_npm_audit_runs_when_package_json(self):
        repo = _git_repo(self.tmp / "app", {"package.json": "{}\n"})
        done = subprocess.CompletedProcess([], 1, stdout=fixture("npm-audit-2high.json"), stderr="")
        with mock.patch("afc.scan.shutil.which", side_effect=lambda n: "/x/npm" if n == "npm" else None), \
                mock.patch("afc.scan._run_tool", return_value=done) as run:
            checks = {c.name: c for c in run_checks(repo)}
        self.assertEqual(checks["npm audit"].status, "fail")
        run.assert_called_once()

    def test_pip_audit_targets_project_not_env(self):
        req = _git_repo(self.tmp / "req", {"requirements.txt": "x\n"})
        self.assertEqual(pip_audit_command(req)[-2:], ["-r", str(req / "requirements.txt")])
        proj = _git_repo(self.tmp / "proj", {"pyproject.toml": "[project]\n"})
        self.assertEqual(pip_audit_command(proj), ["pip-audit", "-f", "json", str(proj)])

    def test_slug(self):
        self.assertEqual(slug("  Orders API: v2!  "), "orders-api-v2")
        self.assertEqual(len(slug("a" * 60)), 40)

    def test_report_written_to_workspace(self):
        ws = self.tmp / "ws"
        checks = [Check("secrets", "pass", "no secrets"), Check("gitleaks", "missing", "")]
        path = write_report(ws, checks, "Orders API")
        self.assertTrue(path.is_relative_to(ws / "reports"))
        self.assertTrue(path.name.endswith("-orders-api.md"))
        text = path.read_text(encoding="utf-8")
        self.assertIn(summary_line(checks), text)
        data = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(data["label"], "Orders API")
        self.assertEqual(data["summary"], summary_line(checks))
        self.assertEqual(data["checks"][0], {"name": "secrets", "status": "pass", "detail": "no secrets"})
        self.assertIn("created", data)

    def test_cli_scan_no_active(self):
        code, out = run_cli(["scan", "--slice", "x"])
        self.assertEqual(code, 1)
        self.assertIn("type /afc", out["error"])

    def test_cli_scan_active(self):
        repo = _git_repo(self.tmp / "app", {"ok.py": "x\n"})
        ws = self.tmp / "ws"
        ws.mkdir()
        reg = Registry()
        reg.add(Project(name="app", code_path=str(repo), workspace_path=str(ws)))
        reg.set_active("app")
        save_registry(self.home, reg)
        with mock.patch("afc.scan.shutil.which", return_value=None):
            code, out = run_cli(["scan", "--slice", "Login"])
        self.assertEqual(code, 0)
        self.assertIn("✅ no secrets", out["summary"])
        self.assertTrue(Path(out["report"]).exists())
