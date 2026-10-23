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


if __name__ == "__main__":
    unittest.main()
