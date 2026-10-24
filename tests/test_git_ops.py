"""Delivery decisions, git wrappers and the deliver/create-remote/detect-team commands."""

import json
import subprocess
from pathlib import Path
from unittest import mock

from afc import cli_delivery
from afc.git_ops import (
    AI_TRAILER,
    commit_message,
    commit_slice,
    decide_branch,
    decide_mode,
    github_repo,
    remote_create_command,
)
from afc.registry import Project, Registry, load_registry, save_registry
from tests.helpers import AfcTestCase, run_cli

REAL_RUN = subprocess.run


def git(code: Path, *args: str) -> str:
    return REAL_RUN(["git", *args], cwd=code, capture_output=True, text=True, check=True).stdout.strip()


class DecisionTests(AfcTestCase):
    def test_mode(self):
        self.assertEqual(decide_mode("unknown", 1, 1), "solo")
        self.assertEqual(decide_mode("unknown", 3, 1), "team")
        self.assertEqual(decide_mode("unknown", 0, 2), "team")
        self.assertEqual(decide_mode("solo", 5, 5), "solo")
        self.assertEqual(decide_mode("team", 1, 1), "team")

    def test_branch(self):
        self.assertEqual(decide_branch("solo", "main", False, False), "main")
        self.assertEqual(decide_branch("solo", "main", True, False), "afc-work")
        self.assertEqual(decide_branch("solo", "main", False, True), "afc-work")
        self.assertIsNone(decide_branch("team", "main", False, False))

    def test_trailer_off_by_default(self):
        self.assertNotIn("Co-Authored-By", commit_message("feat: x", False))
        self.assertEqual(commit_message("feat: x", True), "feat: x\n\n" + AI_TRAILER)

    def test_github_remote_is_private(self):
        cmd = remote_create_command("github", "kong-gateway-lab")
        self.assertIn("--private", cmd)
        self.assertNotIn("--public", cmd)
        self.assertIn("acme/kong-gateway-lab", remote_create_command("github", "kong-gateway-lab", "acme"))

    def test_azure_command_and_unknown_host(self):
        self.assertEqual(
            remote_create_command("azure", "lab", "https://dev.azure.com/acme"),
            ["az", "repos", "create", "--name", "lab", "--org", "https://dev.azure.com/acme"],
        )
        with self.assertRaises(ValueError):
            remote_create_command("gitlab", "lab")

    def test_github_repo_parse(self):
        self.assertEqual(github_repo("git@github.com:sky/lab.git"), ("sky", "lab"))
        self.assertEqual(github_repo("https://github.com/sky/lab"), ("sky", "lab"))
        self.assertIsNone(github_repo("https://dev.azure.com/acme/_git/lab"))


class RepoTestCase(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.code = self.tmp / "lab"
        self.code.mkdir()
        git(self.code, "init", "-q", "-b", "main")
        (self.code / "README.md").write_text("hi\n")

    def project(self, **kw) -> Project:
        fields = dict(name="lab", code_path=str(self.code), workspace_path=str(self.tmp / "ws"),
                      git_name="Sky", git_email="s@example.com")
        fields.update(kw)
        return Project(**fields)

    def register(self, **kw) -> None:
        reg = Registry()
        reg.add(self.project(**kw))
        reg.set_active("lab")
        save_registry(self.home, reg)

    def bare_remote(self) -> Path:
        bare = self.tmp / "remote.git"
        REAL_RUN(["git", "init", "-q", "--bare", str(bare)], check=True)
        git(self.code, "remote", "add", "origin", str(bare))
        git(self.code, "add", "-A")
        git(self.code, "-c", "user.name=S", "-c", "user.email=s@e", "commit", "-qm", "init")
        git(self.code, "push", "-q", "origin", "main")
        git(self.code, "remote", "set-head", "origin", "main")
        return bare

    def change(self, name="f.txt"):
        (self.code / name).write_text(name)


class CommitTests(RepoTestCase):
    def test_commit_uses_project_identity(self):
        sha = commit_slice(self.project(), "feat: first slice")
        self.assertEqual(git(self.code, "log", "-1", "--format=%an%ae"), "Skys@example.com")
        self.assertEqual(git(self.code, "rev-parse", "HEAD"), sha)
        self.assertNotIn("Co-Authored-By", git(self.code, "log", "-1", "--format=%B"))

    def test_commit_adds_trailer_when_on(self):
        commit_slice(self.project(ai_trailer=True), "feat: x")
        self.assertIn(AI_TRAILER, git(self.code, "log", "-1", "--format=%B"))

    def test_commit_refuses_without_identity(self):
        with self.assertRaisesRegex(RuntimeError, "no git name/email"):
            commit_slice(self.project(git_email=""), "feat: x")
        with self.assertRaises(RuntimeError):
            commit_slice(self.project(git_name=""), "feat: x")


class DeliverCliTests(RepoTestCase):
    def test_deliver_without_remote_commits_only(self):
        self.register()
        code, out = run_cli(["deliver", "--message", "feat: x"])
        self.assertEqual(code, 0, out)
        self.assertFalse(out["pushed"])
        self.assertEqual(out["commit"], git(self.code, "rev-parse", "HEAD"))

    def test_deliver_without_identity_is_plain_error(self):
        self.register(git_name="")
        code, out = run_cli(["deliver", "--message", "feat: x"])
        self.assertEqual(code, 1)
        self.assertIn("tell me which to use", out["error"])

    def test_deliver_without_active_project(self):
        code, out = run_cli(["deliver", "--message", "feat: x"])
        self.assertEqual(code, 1)
        self.assertIn("/afc", out["error"])

    def test_solo_pushes_default_branch(self):
        self.register(team_mode="solo")
        bare = self.bare_remote()
        self.change()
        code, out = run_cli(["deliver", "--message", "feat: x"])
        self.assertEqual(code, 0, out)
        self.assertEqual((out["branch"], out["pr_needed"]), ("main", False))
        self.assertEqual(git(bare, "rev-parse", "main"), out["commit"])

    def test_solo_with_deploying_default_pushes_work_branch(self):
        self.register(team_mode="solo")
        bare = self.bare_remote()
        self.change()
        code, out = run_cli(["deliver", "--message", "feat: x", "--default-deploys"])
        self.assertEqual(out["branch"], "afc-work")
        self.assertEqual(git(bare, "rev-parse", "afc-work"), out["commit"])

    def test_team_pushes_feature_branch_and_needs_pr(self):
        self.register(team_mode="team")
        bare = self.bare_remote()
        self.change()
        code, out = run_cli(["deliver", "--message", "feat: Add login page"])
        self.assertEqual(code, 0, out)
        self.assertEqual(out, {"commit": out["commit"], "pushed": True,
                               "branch": "afc/feat-add-login-page", "pr_needed": True})
        self.assertEqual(git(bare, "rev-parse", "afc/feat-add-login-page"), out["commit"])


class DeliverBranchTests(RepoTestCase):
    def test_team_slices_branch_from_origin_main_and_main_stays(self):
        self.register(team_mode="team")
        self.bare_remote()
        main_before = git(self.code, "rev-parse", "main")
        self.change("a.txt")
        _, first = run_cli(["deliver", "--message", "feat: one"])
        self.change("b.txt")
        code, second = run_cli(["deliver", "--message", "feat: two"])
        self.assertEqual(code, 0, second)
        self.assertEqual(second["branch"], "afc/feat-two")
        self.assertEqual(git(self.code, "rev-list", "--count", "origin/main..afc/feat-two"), "1")
        self.assertEqual(git(self.code, "rev-parse", "main"), main_before)

    def test_work_branch_is_switched_to_and_main_stays(self):
        self.register(team_mode="solo")
        self.bare_remote()
        main_before = git(self.code, "rev-parse", "main")
        self.change()
        code, out = run_cli(["deliver", "--message", "feat: x", "--protected"])
        self.assertEqual((code, out["branch"]), (0, "afc-work"))
        self.assertEqual(git(self.code, "rev-parse", "--abbrev-ref", "HEAD"), "afc-work")
        self.assertEqual(git(self.code, "rev-parse", "main"), main_before)

    def test_solo_default_refuses_on_other_branch(self):
        self.register(team_mode="solo")
        bare = self.bare_remote()
        git(self.code, "switch", "-qc", "side")
        self.change()
        code, out = run_cli(["deliver", "--message", "feat: x"])
        self.assertEqual(code, 1)
        self.assertIn("You are on branch side, not main", out["error"])
        self.assertEqual(git(bare, "rev-list", "--count", "main"), "1")

    def test_nothing_to_commit_is_plain(self):
        self.register(team_mode="solo")
        self.bare_remote()
        code, out = run_cli(["deliver", "--message", "feat: x"])
        self.assertEqual((code, out["error"]), (1, "Nothing new to commit."))


def fake_run(outputs: dict):
    """Patch subprocess.run: gh/az return canned output, git runs for real.

    Keys are command prefixes ("gh", "az devops project show"); the longest match wins.
    A value of (code, out) sets the exit code too.
    """
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        line = " ".join(cmd)
        keys = [k for k in outputs if line.startswith(k)]
        if keys:
            val = outputs[max(keys, key=len)]
            rc, out = val if isinstance(val, tuple) else (0, val)
            return subprocess.CompletedProcess(cmd, rc, out, "boom" if rc else "")
        return REAL_RUN(cmd, **kw)

    return mock.patch.object(cli_delivery.subprocess, "run", side_effect=run), calls


def ext(calls):
    return [c for c in calls if c[0] != "git"]


class RemoteCliTests(RepoTestCase):
    def test_create_github_remote_is_private_and_recorded(self):
        self.register()
        patch, calls = fake_run({"gh": ""})
        with patch:
            code, out = run_cli(["create-remote", "--host", "github", "--org", "acme"])
        self.assertEqual(code, 0, out)
        self.assertIn("--private", ext(calls)[0])
        self.assertIn("acme/lab", ext(calls)[0])
        self.assertEqual(load_registry(self.home).get("lab").remote, "github")

    def test_create_azure_remote_adds_origin_and_pushes(self):
        self.register()
        git(self.code, "-c", "user.name=S", "-c", "user.email=s@e", "commit", "-qam", "x", "--allow-empty")
        bare = self.tmp / "az.git"
        REAL_RUN(["git", "init", "-q", "--bare", str(bare)], check=True)
        patch, calls = fake_run(self.az_outputs(bare, "private"))
        with patch:
            code, out = run_cli(["create-remote", "--host", "azure"])
        self.assertEqual(code, 0, out)
        create = [c for c in calls if c[:3] == ["az", "repos", "create"]][0]
        self.assertEqual(create[-2:], ["--project", "Lab"])
        self.assertEqual(git(self.code, "remote", "get-url", "origin"), str(bare))
        self.assertEqual(git(bare, "rev-parse", "main"), git(self.code, "rev-parse", "HEAD"))
        self.assertEqual(load_registry(self.home).get("lab").remote, "azure")

    def az_outputs(self, bare, visibility):
        return {
            "az devops configure": "[defaults]\norganization = https://dev.azure.com/acme\nproject = Lab\n",
            "az devops project show": json.dumps({"name": "Lab", "visibility": visibility}),
            "az repos create": json.dumps({"remoteUrl": str(bare)}),
        }

    def test_azure_public_project_is_refused(self):
        self.register()
        patch, calls = fake_run(self.az_outputs(self.tmp / "x.git", "public"))
        with patch:
            code, out = run_cli(["create-remote", "--host", "azure"])
        self.assertEqual(code, 1)
        self.assertIn("is public", out["error"])
        self.assertFalse([c for c in calls if c[:3] == ["az", "repos", "create"]])
        self.assertEqual(load_registry(self.home).get("lab").remote, "none")

    def test_azure_without_defaults_gives_hint(self):
        self.register()
        patch, _ = fake_run({"az devops configure": "[defaults]\n"})
        with patch:
            code, out = run_cli(["create-remote", "--host", "azure"])
        self.assertEqual(code, 1)
        self.assertIn("az devops configure --defaults", out["error"])

    def test_missing_tool_is_plain_error(self):
        self.register()
        with mock.patch.object(cli_delivery.subprocess, "run", side_effect=FileNotFoundError):
            code, out = run_cli(["create-remote", "--host", "github"])
        self.assertEqual(code, 1)
        self.assertEqual(out["error"], "gh is not installed.")

    def test_detect_team_github_uses_collaborators(self):
        self.register()
        git(self.code, "remote", "add", "origin", "git@github.com:sky/lab.git")
        patch, calls = fake_run({"gh": "3\n"})
        with patch:
            code, out = run_cli(["detect-team"])
        self.assertEqual(code, 0, out)
        self.assertIn("repos/sky/lab/collaborators", ext(calls)[-1])
        self.assertEqual((out["team_mode"], out["confirm"]), ("team", False))
        self.assertEqual(load_registry(self.home).get("lab").team_mode, "team")

    def test_detect_team_local_only_asks_to_confirm(self):
        self.register()
        git(self.code, "-c", "user.name=S", "-c", "user.email=s@e", "commit", "-qm", "x", "--allow-empty")
        patch, calls = fake_run({"gh": "9"})
        with patch:
            code, out = run_cli(["detect-team"])
        self.assertEqual(code, 0, out)
        self.assertFalse([c for c in calls if c[0] == "gh"])
        self.assertEqual(out, {"team_mode": "solo", "recent_authors": 1, "confirm": True})
        self.assertEqual(load_registry(self.home).get("lab").team_mode, "solo")

    def commit_as(self, email: str) -> None:
        git(self.code, "-c", "user.name=X", "-c", f"user.email={email}", "commit", "-qm", email, "--allow-empty")

    def detect(self, outputs: dict | None = None):
        patch, calls = fake_run(outputs or {})
        with patch:
            code, out = run_cli(["detect-team"])
        self.assertEqual(code, 0, out)
        return out, calls

    def test_detect_team_personal_alone_does_not_ask(self):
        self.register(profile="personal")
        self.commit_as("s@e")
        out, calls = self.detect({"gh": "9"})
        self.assertFalse([c for c in calls if c[0] == "gh"])
        self.assertEqual(out, {"team_mode": "solo", "recent_authors": 1, "confirm": False})
        self.assertEqual(load_registry(self.home).get("lab").team_mode, "solo")

    def test_detect_team_personal_brand_new_repo_does_not_ask(self):
        self.register(profile="personal")
        out, _ = self.detect()
        self.assertEqual((out["team_mode"], out["confirm"]), ("solo", False))

    def test_detect_team_personal_with_other_authors_still_asks(self):
        self.register(profile="personal")
        self.commit_as("a@e")
        self.commit_as("b@e")
        out, _ = self.detect()
        self.assertEqual((out["team_mode"], out["confirm"]), ("team", True))

    def test_detect_team_work_profile_alone_still_asks(self):
        self.register(profile="work")
        self.commit_as("s@e")
        out, _ = self.detect()
        self.assertEqual(out["confirm"], True)

    def test_detect_team_recorded_mode_is_kept_and_not_asked(self):
        self.register(team_mode="team")
        git(self.code, "remote", "add", "origin", "git@github.com:sky/lab.git")
        out, calls = self.detect({"gh": "1"})
        self.assertFalse([c for c in calls if c[0] == "gh"])
        self.assertEqual((out["team_mode"], out["confirm"]), ("team", False))
        self.assertEqual(load_registry(self.home).get("lab").team_mode, "team")

    def test_detect_team_recorded_solo_beats_many_authors(self):
        self.register(team_mode="solo")
        self.commit_as("a@e")
        self.commit_as("b@e")
        out, _ = self.detect()
        self.assertEqual((out["team_mode"], out["confirm"]), ("solo", False))
