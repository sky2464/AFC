import re
import unittest
from pathlib import Path

from afc.profile import ALL_MODULES

ROOT = Path(__file__).resolve().parent.parent


def rule(name: str) -> str:
    return (ROOT / "rules" / f"{name}.md").read_text()


class RuleModulesTest(unittest.TestCase):
    def test_rule_modules_complete(self):
        for m in ALL_MODULES:
            text = rule(m)
            heads = re.findall(r"^## (.+)$", text, re.M)
            self.assertEqual(heads, ["Applies when", "Do", "Never", "Check"], m)
            self.assertLessEqual(len(text.splitlines()), 80, m)

    def test_no_extra_rule_files(self):
        names = {p.stem for p in (ROOT / "rules").glob("*.md")}
        self.assertEqual(names, set(ALL_MODULES))

    def test_identity_covers_enterprise_terms(self):
        t = rule("identity")
        for term in ["SSO", "SAML", "OIDC", "Entra", "Active Directory", "JWT"]:
            self.assertIn(term, t)

    def test_api_covers_cors_and_rate_limit(self):
        t = rule("api")
        for term in ["CORS", "rate limit", "error envelope", "version", "gateway"]:
            self.assertIn(term, t)

    def test_secrets_covers_env_and_rotation(self):
        t = rule("secrets")
        for term in [".env", "secrets manager", "rotat"]:
            self.assertIn(term, t)

    def test_dependencies_never_from_memory(self):
        t = rule("dependencies")
        for term in ["from memory", "pin", "SBOM", "pip-audit", "npm audit"]:
            self.assertIn(term, t)

    def test_architecture_has_threat_table_and_limits(self):
        t = rule("architecture")
        self.assertIn("| Threat | Category | Mitigation |", t)
        for term in ["500 lines", "ADR", "STRIDE"]:
            self.assertIn(term, t)

    def test_api_cors_exact_origins_and_identity_csrf(self):
        self.assertIn("evil-example.com", rule("api"))
        self.assertIn("null", rule("api"))
        for term in ["CSRF", "GET", "MFA"]:
            self.assertIn(term, rule("identity"))

    def test_ai_safety_data_not_instructions(self):
        self.assertIn("data, not instructions", rule("ai-safety"))

    def test_each_check_names_a_verifier(self):
        verifiers = ["Tests:", "Review question:", "guard blocks", "secret scan",
                     "gitleaks", "npm audit", "pip-audit", "semgrep"]
        for m in ALL_MODULES:
            check = rule(m).split("## Check", 1)[1]
            self.assertTrue(any(v in check for v in verifiers), m)


SKILLS = ["afc-start", "afc-interview", "afc-slice", "afc-drift", "afc-deliver",
          "afc-enterprise", "afc-architecture", "afc-capabilities"]
COMMANDS = ["afc"]
TEXT_DIRS = ["afc", "tests", "rules", ".claude", "templates"]
TEXT_SUFFIXES = {".py", ".md", ".json", ".txt", ".toml", ".yml", ".yaml", ""}


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    if not text.startswith("---\n"):
        return {}
    block = text.split("---\n", 2)[1]
    return dict(line.split(":", 1) for line in block.splitlines() if ":" in line)


class BrainTest(unittest.TestCase):
    def test_claude_md_routes_every_skill(self):
        t = (ROOT / "CLAUDE.md").read_text()
        for s in SKILLS:
            self.assertIn(s, t)
        self.assertLessEqual(len(t.splitlines()), 150)

    def test_commands_exist(self):
        for c in COMMANDS:
            self.assertTrue((ROOT / ".claude/commands" / f"{c}.md").exists(), c)

    def test_only_one_visible_command(self):
        names = sorted(p.stem for p in (ROOT / ".claude/commands").glob("*.md"))
        self.assertEqual(names, COMMANDS)

    def test_claude_md_states_two_option_rule(self):
        self.assertIn("at most two numbered next steps", (ROOT / "CLAUDE.md").read_text())

    def test_claude_md_hard_rules(self):
        t = (ROOT / "CLAUDE.md").read_text()
        for term in ["Flight Control blocked", "one question per message", "sh bin/afc modules",
                     "data, not instructions", "public", "force-push", "production deploy",
                     "never send", "code_path", "/afc"]:
            self.assertIn(term, t)

    def test_skill_frontmatter(self):
        dirs = [d for d in (ROOT / ".claude/skills").iterdir() if d.is_dir()]
        names = [d.name for d in dirs]
        for s in SKILLS:
            self.assertIn(s, names)
        for d in dirs:
            fm = frontmatter(d / "SKILL.md")
            self.assertEqual(fm.get("name", "").strip(), d.name, d)
            desc = fm.get("description", "").strip()
            self.assertTrue(desc.startswith("Use when"), d)
            self.assertNotIn("\n", desc)
            self.assertEqual(fm.get("user-invocable", "").strip(), "false", d)

    def test_start_skill_flows(self):
        t = (ROOT / ".claude/skills/afc-start/SKILL.md").read_text()
        for term in ["sh bin/afc new", "sh bin/afc adopt", "granted", "/add-dir",
                     "afc-architecture", "afc-interview", "Welcome back"]:
            self.assertIn(term, t)

    def test_progress_template_sections(self):
        t = (ROOT / "templates/workspace/plan/progress.md").read_text()
        heads = re.findall(r"^## (.+)$", t, re.M)
        self.assertEqual(heads, ["Now", "Next", "Done"])

    def test_slice_skill_names_three_checkpoints(self):
        t = (ROOT / ".claude/skills/afc-slice/SKILL.md").read_text()
        for term in ["checkpoint 1", "checkpoint 2", "checkpoint 3", "afc scan", "afc modules"]:
            self.assertIn(term, t)

    def test_capabilities_has_promotion_gate(self):
        t = (ROOT / ".claude/skills/afc-capabilities/SKILL.md").read_text()
        for term in ["library/skills", "scrub", "maintenance mode"]:
            self.assertIn(term, t)

    def test_enterprise_never_sends(self):
        t = (ROOT / ".claude/skills/afc-enterprise/SKILL.md").read_text()
        for term in ["draft", "never send"]:
            self.assertIn(term, t)

    def test_working_skills_size(self):
        for s in SKILLS[1:]:
            t = (ROOT / ".claude/skills" / s / "SKILL.md").read_text()
            self.assertLessEqual(len(t.splitlines()), 250, s)

    def test_afc_command_menu(self):
        t = (ROOT / ".claude/commands/afc.md").read_text()
        for term in ["sh bin/afc status", "More", "sh bin/afc list", "sh bin/afc switch",
                     "sh bin/afc open", "sh bin/afc maintain"]:
            self.assertIn(term, t)

    def test_no_active_project_offers_switch(self):
        cmd = (ROOT / ".claude/commands/afc.md").read_text()
        start = (ROOT / ".claude/skills/afc-start/SKILL.md").read_text()
        for t in (cmd, start):
            self.assertIn('"active": null', t)
            self.assertIn("sh bin/afc switch", t)
        for key in ("team_mode", "git_name", "git_email", "ai_trailer"):
            self.assertIn(f"`{key}`", cmd)

    def test_drift_and_interview_wording(self):
        drift = (ROOT / ".claude/skills/afc-drift/SKILL.md").read_text()
        self.assertLess(drift.index("keep its output as \"before\""),
                        drift.index("sh bin/afc set profile"))
        self.assertIn("If nothing drifted, say nothing", drift)
        interview = (ROOT / ".claude/skills/afc-interview/SKILL.md").read_text()
        for term in ("a quick prototype", "an MVP"):
            self.assertIn(term, interview)
        self.assertIn("from your own", (ROOT / "README.md").read_text())

    def test_own_naming(self):
        paths = [ROOT / "CLAUDE.md", *ROOT.glob(".claude/**/*.md"), *ROOT.glob("rules/*.md"),
                 *ROOT.glob("templates/**/*")]
        for p in paths:
            if p.is_file():
                self.assertNotIn("graphify-out", p.read_text(), p)

    def test_no_file_over_500_lines(self):
        for d in TEXT_DIRS:
            for p in (ROOT / d).rglob("*"):
                if p.is_file() and p.suffix in TEXT_SUFFIXES and "__pycache__" not in p.parts:
                    self.assertLessEqual(len(p.read_text().splitlines()), 500, p)


if __name__ == "__main__":
    unittest.main()
