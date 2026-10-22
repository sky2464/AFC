import os
import subprocess

from afc.fingerprint import MIN_LINE, build_fingerprints, leaks, load_fingerprints, normalize
from afc.hooks.common import Context
from afc.hooks.rules_git import check_git
from afc.hooks.rules_resources import check_resources
from afc.registry import Project
from tests.helpers import AfcTestCase, bash, ev

POLICY = "All production services must authenticate through Contoso Entra tenant only."


class TestFingerprint(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.ws = self.home / "projects" / "demo"
        (self.ws / "resources").mkdir(parents=True)
        (self.ws / "plan").mkdir()
        self.app = self.tmp / "app"
        (self.app / "docs").mkdir(parents=True)
        project = Project(name="demo", code_path=str(self.app), workspace_path=str(self.ws))
        self.ctx = Context(home=self.home.resolve(), root=self.tmp / "afc",
                           active=project, maintain=False)
        (self.ws / "resources/policy.md").write_text(POLICY + "\n")

    def write(self, path, content):
        return check_resources(ev("Write", {"file_path": str(path), "content": content}), self.ctx)

    def test_normalize(self):
        self.assertEqual(normalize("  A   b\tC \n"), "a b c")
        self.assertEqual(MIN_LINE, 40)

    def test_copied_policy_line_blocked(self):
        r = self.write(self.app / "README.md",
                       "Note: all production services must authenticate through Contoso Entra tenant only.")
        self.assertIn("company resource", r)

    def test_exact_line_blocked(self):
        self.assertIn("company resource text", self.write(self.app / "x.md", "intro\n" + POLICY.upper()))

    def test_whole_file_blocked(self):
        (self.ws / "resources/short.txt").write_text("tiny\n")
        self.assertTrue(leaks("tiny\n", build_fingerprints(self.ws / "resources")))

    def test_short_lines_ignored(self):
        (self.ws / "resources/notes.md").write_text("Contoso tenant policy\n" + "x" * 50 + "\n")
        self.assertIsNone(self.write(self.app / "a.md", "Contoso tenant policy\nother"))

    def test_summary_in_workspace_allowed(self):
        self.assertIsNone(self.write(self.ws / "plan/decisions.md", POLICY))

    def test_edit_new_string_checked(self):
        r = check_resources(ev("Edit", {"file_path": str(self.app / "a.md"),
                                        "old_string": "x", "new_string": POLICY}), self.ctx)
        self.assertIsNotNone(r)

    def test_cp_from_resources_blocked(self):
        r = check_resources(bash(f"cp {self.ws}/resources/policy.md {self.app}/docs/"), self.ctx)
        self.assertIn("company resource file", r)

    def test_cp_relative_and_wrapped(self):
        for cmd in ("cp resources/policy.md " + str(self.app),
                    "sudo cp -r resources " + str(self.app),
                    f"cd {self.ws} && rsync -a resources/ {self.app}/docs",
                    f"sh -c 'mv resources/policy.md {self.app}'"):
            self.assertIsNotNone(check_resources(bash(cmd, cwd=self.ws), self.ctx), cmd)

    def test_cp_within_workspace_allowed(self):
        cmd = f"cp {self.ws}/resources/policy.md {self.ws}/plan/"
        self.assertIsNone(check_resources(bash(cmd), self.ctx))

    def test_cache_rebuilds_on_change(self):
        new = "Quarterly vendor reviews require sign-off from the Fabrikam risk office."
        self.assertIsNone(self.write(self.app / "a.md", new))
        self.assertTrue((self.ws / ".afc-fingerprints.json").is_file())
        path = self.ws / "resources/policy.md"
        path.write_text(POLICY + "\n" + new + "\n")
        st = path.stat()
        os.utime(path, (st.st_atime, st.st_mtime + 5))
        self.assertIsNotNone(self.write(self.app / "a.md", new))
        (self.ws / "resources/extra.md").write_text("Every contractor laptop is enrolled in Intune before day one.\n")
        self.assertTrue(leaks("Every contractor laptop is enrolled in Intune before day one.",
                              load_fingerprints(self.ws)))

    def test_no_active_project_allows(self):
        self.ctx.active = None
        self.assertIsNone(self.write(self.app / "a.md", POLICY))

    def test_commit_scan_catches_resource_text(self):
        repo = self.app
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "f.md").write_text(POLICY + "\n")
        subprocess.run(["git", "-C", str(repo), "add", "f.md"], check=True)
        reason = check_git(bash("git commit -m x", cwd=repo), self.ctx)
        self.assertIsNotNone(reason)
        self.assertIn("company resource", reason)
