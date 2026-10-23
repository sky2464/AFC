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
        body = "".join(f"row {i}\n" for i in range(12))
        (self.ws / "resources/rows.txt").write_text(body)
        self.assertTrue(leaks(body, build_fingerprints(self.ws / "resources")))

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

    def test_empty_and_tiny_resources_ignored(self):
        (self.ws / "resources/empty.md").write_text("")
        (self.ws / "resources/short.md").write_text("short\n")
        fps = load_fingerprints(self.ws)
        self.assertFalse(leaks("", fps))
        self.assertFalse(leaks("short\n", fps))
        self.assertIsNone(self.write(self.app / "e.md", ""))

    def test_edit_removing_leaked_text_allowed(self):
        r = check_resources(ev("Edit", {"file_path": str(self.app / "a.md"),
                                        "old_string": POLICY, "new_string": "see workspace"}), self.ctx)
        self.assertIsNone(r)
        r = check_resources(ev("Edit", {"file_path": str(self.app / "a.md"),
                            "edits": [{"old_string": "x", "new_string": POLICY}]}), self.ctx)
        self.assertIsNotNone(r)

    def test_other_bash_copies_blocked(self):
        res = f"{self.ws}/resources/policy.md"
        for cmd in (f"cat {res} > {self.app}/README.md", f"cat {res} | tee {self.app}/x",
                    f"dd if={res} of={self.app}/x", f"install {res} {self.app}/x",
                    f"ln -s {res} {self.app}/x", f"tar czf {self.app}/r.tgz {self.ws}/resources",
                    f"zip -r {self.app}/r.zip {self.ws}/resources", f"scp {res} host:/tmp/",
                    f"cat < {res} > {self.app}/x",
                    f'echo "{POLICY}" >> {self.app}/x',
                    f"cat > {self.app}/x <<'EOF'\n{POLICY}\nEOF"):
            self.assertIsNotNone(check_resources(bash(cmd), self.ctx), cmd)
        for cmd in (f"cat {res}", f"grep tenant {res}", f"cat {res} > {self.ws}/plan/x"):
            self.assertIsNone(check_resources(bash(cmd), self.ctx), cmd)

    def test_read_only_two_path_commands_allowed(self):
        res = f"{self.ws}/resources/policy.md"
        for cmd in (f"diff {res} {self.app}/b", f"grep x {res} {self.app}/y",
                    f"cmp {res} {self.app}/b"):
            self.assertIsNone(check_resources(bash(cmd), self.ctx), cmd)
        for cmd in (f"ditto {res} {self.app}/b", f"mv {res} {self.app}/b"):
            self.assertIsNotNone(check_resources(bash(cmd), self.ctx), cmd)

    def test_wrapped_sentence_and_bullet_caught(self):
        (self.ws / "resources/wrap.md").write_text(
            "Customer exports must be encrypted at rest\nwith keys held in the Northwind vault.\n")
        self.assertIsNotNone(self.write(self.app / "a.md",
            "Customer exports must be encrypted at rest with keys held in the Northwind vault."))
        self.assertIsNotNone(self.write(self.app / "b.md", "- " + POLICY))
        self.assertIsNotNone(self.write(self.app / "c.md", "# 1. " + POLICY))

    def test_cache_format_and_stale_rebuild(self):
        cache = self.ws / ".afc-fingerprints.json"
        cache.write_text('{"mtimes": {}, "fingerprints": []}')
        self.assertTrue(leaks(POLICY, load_fingerprints(self.ws)))
        import json
        data = json.loads(cache.read_text())
        self.assertEqual(data["v"], 2)
        entry = data["files"]["policy.md"]
        self.assertIn("mtime_ns", entry)
        self.assertIn("size", entry)

    def test_unchanged_files_not_rehashed(self):
        from unittest.mock import patch
        load_fingerprints(self.ws)
        (self.ws / "resources/new.md").write_text("Another long enough company policy sentence goes here.\n")
        import afc.fingerprint as f
        with patch.object(f, "_file_fingerprints", wraps=f._file_fingerprints) as spy:
            load_fingerprints(self.ws)
        self.assertEqual([c.args[0].name for c in spy.call_args_list], ["new.md"])

    def test_no_fingerprint_load_without_outside_target(self):
        from unittest.mock import patch
        with patch("afc.hooks.rules_resources.load_fingerprints") as spy:
            check_resources(bash("ls -la"), self.ctx)
            self.write(self.ws / "plan/x.md", POLICY)
        spy.assert_not_called()

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
