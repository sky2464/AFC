"""AGENTS.md stays in step with CLAUDE.md (FC-051 slice 5)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from afc import instructions
from afc.config import afc_root


class InstructionsTests(unittest.TestCase):
    def test_the_repo_files_match_claude_md(self):
        self.assertEqual(instructions.out_of_date(afc_root()), [], "run: sh bin/afc instructions --write")

    def test_a_change_to_claude_md_is_noticed_and_fixed(self):
        tmp = Path(tempfile.mkdtemp(prefix="afc-instr-")).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "CLAUDE.md").write_text("# Rules\n- one\n")
        self.assertEqual(len(instructions.out_of_date(tmp)), 2)
        instructions.write(tmp)
        self.assertEqual(instructions.out_of_date(tmp), [])
        self.assertIn("- one", (tmp / "AGENTS.md").read_text())
        (tmp / "CLAUDE.md").write_text("# Rules\n- two\n")
        self.assertEqual([p.name for p in instructions.out_of_date(tmp)], ["AGENTS.md"])


if __name__ == "__main__":
    unittest.main()
