import unittest

from afc.config import afc_root
from afc.hooks.common import Context
from afc.hooks.pretool import RULES
from afc.hooks.rules_secrets import check_secrets
from afc.registry import Project
from afc.secrets import find_secrets
from tests.helpers import AfcTestCase, ev

AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
PEM = "-----BEGIN RSA " + "PRIVATE KEY-----"
GENERIC = "api_key = " + '"q8Zr2LmN0pX4sT7v"'


class SecretsTestCase(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.app = self.tmp / "app"
        self.app.mkdir()
        project = Project(name="demo", code_path=str(self.app), workspace_path=str(self.tmp / "ws"))
        self.ctx = Context(home=self.home, root=afc_root(), active=project, maintain=False)

    def test_aws_key_flagged(self):
        self.assertEqual(find_secrets(f'k = "{AWS}"'), ["aws-access-key"])

    def test_private_key_flagged(self):
        self.assertIn("private-key", find_secrets(PEM))

    def test_github_and_slack_flagged(self):
        self.assertIn("github-token", find_secrets("gh" + "p_" + "a" * 36))
        self.assertIn("slack-token", find_secrets("xo" + "xb-" + "1234567890ab"))

    def test_generic_flagged(self):
        self.assertIn("generic-assignment", find_secrets(GENERIC))

    def test_identifier_suffix_assignments_flagged(self):
        value = '"q8Zr2LmN' + '0pX4sT7v"'
        for name in ("SECRET_KEY", "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN_VALUE"):
            self.assertIn("generic-assignment", find_secrets(f"{name} = {value}"), name)

    def test_unquoted_env_lines_flagged(self):
        value = "q8Zr2LmN" + "0pX4sT7v"
        self.assertIn("generic-assignment", find_secrets(f"API_KEY={value}\n"))
        self.assertIn("generic-assignment", find_secrets(f"export DB_PASSWORD={value}"))
        for name in ("config.yaml", "app.yml", "a.ini", "setup.cfg", ".env", ".env.local"):
            self.assertIn("generic-assignment", find_secrets(f"password: {value}", name), name)
            self.assertIn("generic-assignment", find_secrets(f"api_key = {value}", name), name)
        self.assertEqual(find_secrets(f"password: {value}", "notes.md"), [])
        self.assertEqual(find_secrets("token = get_token_from_vault()"), [])
        self.assertEqual(find_secrets("API_KEY=" + "your-api-key-here-x"), [])
        self.assertEqual(find_secrets("password: ${DB_PASSWORD_VALUE}", "c.yaml"), [])

    def test_unquoted_config_secret_blocked_by_write_guard(self):
        content = "API_TOKEN: " + "q8Zr2LmN" + "0pX4sT7v"
        event = ev("Write", {"file_path": str(self.app / "conf.yaml"), "content": content})
        self.assertIsNotNone(check_secrets(event, self.ctx))

    def test_placeholders_not_flagged(self):
        for s in ['api_key = "your-api-key-here"', 'token: "${API_TOKEN}"',
                  'password = "<password-goes-here>"', 'secret = "process.env.SECRET_VALUE"']:
            self.assertEqual(find_secrets(s), [], s)

    def test_clean_text(self):
        self.assertEqual(find_secrets("print('hello')"), [])

    def test_reason_does_not_echo_value(self):
        r = check_secrets(ev("Write", {"file_path": str(self.app / "a.py"), "content": f'k="{AWS}"'}), self.ctx)
        self.assertIn("aws-access-key", r)
        self.assertNotIn(AWS, r)

    def test_edit_new_string_scanned(self):
        e = ev("Edit", {"file_path": str(self.app / "a.py"), "old_string": "x", "new_string": PEM})
        self.assertIn("private-key", check_secrets(e, self.ctx))

    def test_clean_write_allowed(self):
        e = ev("Write", {"file_path": str(self.app / "a.py"), "content": "x = 1"})
        self.assertIsNone(check_secrets(e, self.ctx))

    def test_bash_out_of_scope(self):
        self.assertIsNone(check_secrets(ev("Bash", {"command": f"echo {AWS}"}), self.ctx))

    def test_wired_into_rules(self):
        self.assertIn(check_secrets, RULES)


if __name__ == "__main__":
    unittest.main()
