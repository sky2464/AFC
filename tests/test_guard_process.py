"""The process rule: stopping programs by name or pattern is blocked; stopping one by its ID is not."""

from afc.hooks.common import Context
from afc.hooks.rules_process import check_process
from tests.helpers import AfcTestCase, bash, ev

BLOCKED = ["pkill -f node", 'pkill -f "next dev"', "pkill node", "killall node", "killall -9 python3",
           "sudo pkill -f server", "cd app && pkill -f 'next dev'", "sh -c 'pkill -f vite'",
           "npm run build; pkill node", "/usr/bin/pkill -f x", "timeout 5 killall node"]
ALLOWED = ["kill 4242", "kill -9 4242", "kill $(cat server.pid)", "npm run dev &\necho $! > server.pid",
           "pgrep -f node", "ps aux | grep node", "echo pkill -f node",
           'git commit -m "stop with pkill -f"', "cat > notes.md <<'EOF'\npkill -f node\nEOF"]


class TestProcessRule(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.ctx = Context(home=self.home, root=self.tmp, active=None, maintain=False)

    def test_pattern_kills_are_blocked_with_a_plain_reason(self):
        for command in BLOCKED:
            with self.subTest(command=command):
                reason = check_process(bash(command), self.ctx)
                self.assertIsNotNone(reason)
                self.assertIn("process ID", reason)

    def test_killing_by_id_and_looking_are_allowed(self):
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(check_process(bash(command), self.ctx))

    def test_other_tools_and_unreadable_commands_are_left_to_other_rules(self):
        self.assertIsNone(check_process(ev("Write", {"file_path": "/x", "content": "pkill node"}), self.ctx))
        self.assertIsNone(check_process(bash("pkill 'unterminated"), self.ctx))
