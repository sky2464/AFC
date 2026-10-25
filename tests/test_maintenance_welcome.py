"""The welcome and context show maintenance mode; /afc mm and the start flow handle it."""

import io
import json
import re
from pathlib import Path
from unittest.mock import patch

from afc import config
from afc.hooks import session_start
from afc.hooks.session_start import build_output, main
from afc.registry import Project, Registry, save_registry
from tests.helpers import AfcTestCase, clean_afc_git

ROOT = Path(__file__).resolve().parent.parent
A, B = "11111111-aaaa-bbbb-cccc-000000000001", "22222222-aaaa-bbbb-cccc-000000000002"
REAL_BRANCH = session_start._branch  # setUp replaces the module attribute


class MaintenanceWelcomeTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        reg = Registry()
        reg.add(Project(name="kong-gateway-lab", code_path="/c/kong", workspace_path="/w/kong",
                        profile="api", last_slice="add rate limit"))
        reg.set_active("kong-gateway-lab")
        save_registry(self.home, reg)
        config.set_maintain(self.home, True, A)
        patcher = patch.object(session_start, "_branch", return_value="dev")
        patcher.start()
        self.addCleanup(patcher.stop)
        git_patch = clean_afc_git()
        git_patch.start()
        self.addCleanup(git_patch.stop)

    def ctx(self, out: dict) -> str:
        return out["hookSpecificOutput"]["additionalContext"]

    def test_welcome_names_the_mode_folder_and_branch(self):
        message = build_output(self.home, A)["systemMessage"]
        self.assertIn("🔧 Maintenance: working on Flight Control itself", message)
        self.assertIn(ROOT.name, message)
        self.assertIn("dev", message)
        self.assertIn("/afc mm off", message)
        self.assertEqual(len(message.splitlines()), 4)

    def test_no_project_is_offered(self):
        out = build_output(self.home, A)
        self.assertNotIn("Type 1", out["systemMessage"])
        self.assertNotIn("kong-gateway-lab", out["systemMessage"])
        self.assertNotIn("kong-gateway-lab", self.ctx(out))
        self.assertNotIn("The welcome asked", self.ctx(out))

    def test_context_tells_claude_to_stay_on_flight_control(self):
        ctx = self.ctx(build_output(self.home, A))
        self.assertIn("Mode: maintenance", ctx)
        self.assertIn("docs/master-plan.md", ctx)
        self.assertIn("branch dev", ctx)
        self.assertIn("do not read, build or change any project", ctx)

    def test_context_skips_the_health_note(self):
        (self.home / "projects" / "ghost-app").mkdir(parents=True)
        self.assertNotIn("Health check", self.ctx(build_output(self.home, A)))

    def test_another_session_gets_the_normal_welcome(self):
        out = build_output(self.home, B)
        self.assertNotIn("🔧", out["systemMessage"])
        self.assertIn("Type 1 to continue kong-gateway-lab", out["systemMessage"])
        self.assertNotIn("Mode: maintenance", self.ctx(out))
        self.assertNotIn("🔧", build_output(self.home)["systemMessage"])

    def test_global_switch_shows_the_mode_for_every_session(self):
        config.set_maintain(self.home, False, A)
        config.set_maintain(self.home, True, None)
        for session in (A, B, None):
            self.assertIn("🔧", build_output(self.home, session)["systemMessage"])

    def test_unreadable_branch_does_not_break_the_welcome(self):
        with patch.object(session_start, "_branch", return_value="unknown"):
            self.assertIn("unknown", build_output(self.home, A)["systemMessage"])

    def test_branch_lookup_survives_git_problems(self):
        with patch("afc.hooks.session_start.subprocess.run", side_effect=OSError("no git")):
            self.assertEqual(REAL_BRANCH(ROOT), "unknown")
        self.assertEqual(REAL_BRANCH(self.tmp), "unknown")  # not a git folder

    def test_main_reads_the_session_from_the_hook_input(self):
        buf = io.StringIO()
        self.assertEqual(main(buf, json.dumps({"session_id": A})), 0)
        self.assertIn("🔧", json.loads(buf.getvalue())["systemMessage"])
        buf = io.StringIO()
        main(buf, json.dumps({"session_id": B}))
        self.assertNotIn("🔧", json.loads(buf.getvalue())["systemMessage"])


class MaintenanceInstructionsTest(AfcTestCase):
    def read(self, rel: str) -> str:
        return (ROOT / rel).read_text()

    def test_afc_mm_switches_the_mode(self):
        t = self.read(".claude/commands/afc.md")
        for term in ("/afc mm", "mm off", "sh bin/afc maintain on", "sh bin/afc maintain off",
                     "sh bin/afc maintain status", "set aside", "scope"):
            self.assertIn(term, t)

    def test_afc_in_maintenance_mode_does_not_show_projects(self):
        t = self.read(".claude/commands/afc.md")
        head = t.split("## More…")[0]
        self.assertLess(head.index("sh bin/afc maintain status"), head.index("sh bin/afc status"))

    def test_start_skill_has_a_maintenance_case(self):
        t = self.read(".claude/skills/afc-start/SKILL.md")
        self.assertIn("Mode: maintenance", t)
        self.assertIn("/afc mm off", t)

    def test_menu_numbers_stay_in_order(self):
        more = self.read(".claude/commands/afc.md").split("## More…")[1]
        nums = [int(n) for n in re.findall(r"^(\d+)\. \*\*", more, re.M)]
        self.assertEqual(nums, list(range(1, len(nums) + 1)))
