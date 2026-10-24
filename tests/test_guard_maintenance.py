"""In maintenance mode the guard keeps Flight Control work away from every project's folders."""

import unittest
from pathlib import Path

from afc.hooks.common import Context, load_context
from afc.hooks.pretool import RULES
from afc.hooks.rules_maintenance import check_maintenance
from afc.registry import Project, Registry, save_registry
from tests.helpers import AfcTestCase, bash, ev

ROOT = Path(__file__).resolve().parent.parent


class MaintenanceGuardTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.app = self.tmp / "app"
        self.workspace = self.home / "projects" / "demo"
        self.other_app = self.tmp / "other-app"
        for folder in (self.app, self.workspace, self.other_app, self.tmp / "free"):
            folder.mkdir(parents=True)
        demo = Project(name="demo", code_path=str(self.app), workspace_path=str(self.workspace))
        other = Project(name="other", code_path=str(self.other_app),
                        workspace_path=str(self.home / "projects" / "other"))
        self.ctx = Context(home=self.home, root=ROOT, active=demo, maintain=True,
                           projects=(demo, other))

    def blocked(self, event: dict, ctx: Context | None = None) -> str:
        reason = check_maintenance(event, ctx or self.ctx)
        self.assertIsNotNone(reason, event)
        return reason

    # -- writes

    def test_writes_into_projects_are_blocked_in_maintenance_mode(self):
        for target in (self.app / "x.ts", self.workspace / "plan" / "intent.md",
                       self.other_app / "y.py"):
            for tool in ("Write", "Edit"):
                reason = self.blocked(ev(tool, {"file_path": str(target)}))
                self.assertIn("maintenance mode is on", reason)
        self.assertIn("project demo", self.blocked(ev("Write", {"file_path": str(self.app / "a")})))

    def test_shell_writes_into_projects_are_blocked(self):
        self.blocked(bash(f"echo hi > {self.app}/x.txt"))
        self.blocked(bash(f"cp notes.md {self.other_app}/"))
        self.blocked(bash(f"cd {self.app} && echo hi > x.txt"))

    def test_writes_to_flight_control_and_free_folders_stay_allowed(self):
        for target in (ROOT / "docs" / "x.md", self.tmp / "free" / "x.txt"):
            self.assertIsNone(check_maintenance(ev("Write", {"file_path": str(target)}), self.ctx))
        self.assertIsNone(check_maintenance(bash(f"echo hi > {self.tmp}/free/x"), self.ctx))

    def test_reading_a_project_is_not_blocked(self):
        for command in (f"cat {self.app}/README.md", f"ls {self.app}", f"grep -r x {self.workspace}"):
            self.assertIsNone(check_maintenance(bash(command), self.ctx), command)

    def test_nothing_changes_outside_maintenance_mode(self):
        normal = Context(home=self.home, root=ROOT, active=self.ctx.active, maintain=False,
                         projects=self.ctx.projects)
        self.assertIsNone(check_maintenance(ev("Write", {"file_path": str(self.app / "a")}), normal))
        self.assertIsNone(check_maintenance(bash(f"git -C {self.app} status"), normal))

    # -- git

    def test_git_in_a_project_folder_is_blocked(self):
        for command in (
            f"git -C {self.app} status",
            f"git -C {self.app}/ log --oneline",
            f"cd {self.app} && git status",
            f"cd {self.app} && git commit -m x",
            f"git --git-dir={self.app}/.git log",
            f"git --git-dir {self.other_app}/.git --work-tree {self.other_app} diff",
            f"git -C {self.tmp} -C app status",
            f"sh -c 'cd {self.app} && git add .'",
        ):
            reason = self.blocked(bash(command))
            self.assertIn("git", reason, command)
        self.blocked(bash("git status", cwd=self.app))
        self.blocked(bash("git status", cwd=self.app / "src"))

    def test_git_in_the_workspace_is_blocked_too(self):
        self.blocked(bash(f"git -C {self.workspace} status"))

    def test_git_in_flight_control_or_elsewhere_is_allowed(self):
        for command in (f"git -C {ROOT} status", f"cd {ROOT} && git log", f"git -C {self.tmp / 'free'} status",
                        "git status", "git -C . diff"):
            self.assertIsNone(check_maintenance(bash(command, cwd=ROOT), self.ctx), command)

    def test_a_path_that_only_shares_a_prefix_is_not_a_project(self):
        sibling = Path(str(self.app) + "-copy")
        sibling.mkdir()
        self.assertIsNone(check_maintenance(bash(f"git -C {sibling} status"), self.ctx))
        self.assertIsNone(check_maintenance(ev("Write", {"file_path": str(sibling / "a")}), self.ctx))

    def test_a_project_folder_that_holds_flight_control_is_ignored(self):
        broad = Project(name="broad", code_path=str(ROOT.parent), workspace_path=str(self.workspace))
        ctx = Context(home=self.home, root=ROOT, active=broad, maintain=True, projects=(broad,))
        self.assertIsNone(check_maintenance(ev("Write", {"file_path": str(ROOT / "docs" / "x")}), ctx))
        self.assertIsNone(check_maintenance(bash("git status", cwd=ROOT), ctx))

    def test_unreadable_commands_are_left_to_the_path_rule(self):
        self.assertIsNone(check_maintenance(bash('echo "unclosed > /x'), self.ctx))

    # -- wiring

    def test_rule_is_registered_and_context_lists_every_project(self):
        self.assertIn(check_maintenance, RULES)
        reg = Registry()
        for name in ("a-app", "b-app"):
            reg.add(Project(name=name, code_path=str(self.tmp / name),
                            workspace_path=str(self.home / "projects" / name)))
        save_registry(self.home, reg)
        self.assertEqual([p.name for p in load_context(None).projects], ["a-app", "b-app"])


if __name__ == "__main__":
    unittest.main()
