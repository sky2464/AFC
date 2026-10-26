"""`afc check` says how each other AI tool is covered (FC-051 slice 7)."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from afc import instructions, tool_coverage
from afc.config import afc_root


class ToolCoverageTests(unittest.TestCase):
    def repo(self):
        tmp = Path(tempfile.mkdtemp(prefix="afc-cov-")).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        (tmp / "CLAUDE.md").write_text("# Rules\n")
        return tmp

    def test_a_bare_repo_reports_everything_missing(self):
        for item in tool_coverage.coverage(self.repo()):
            self.assertEqual((item["instructions"], item["hooks"], item["commit_check"]),
                             ("missing", "missing", "missing"))

    def test_a_stale_file_and_a_commit_check_that_is_off_are_named(self):
        root = self.repo()
        instructions.write(root)
        (root / "CLAUDE.md").write_text("# Rules\n- new\n")
        (root / ".githooks").mkdir()
        (root / ".githooks" / "pre-commit").write_text("#!/bin/sh\n")
        found = tool_coverage.coverage(root)
        # the Copilot pointer never copies CLAUDE.md, so it cannot go stale
        self.assertEqual({i["tool"]: i["instructions"] for i in found},
                         {"Cursor": "out of date", "Codex": "out of date", "GitHub Copilot": "ok",
                          "Antigravity": "out of date"})
        self.assertEqual({i["commit_check"] for i in found}, {"off"})
        self.assertTrue(any("git config core.hooksPath" in line for line in tool_coverage.lines(found)))
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=root, check=True)
        self.assertEqual({i["commit_check"] for i in tool_coverage.coverage(root)}, {"on"})

    def test_this_repo_has_instructions_and_hooks_for_all_four(self):
        found = tool_coverage.coverage(afc_root())
        self.assertEqual(len(found), 4)
        for item in found:
            self.assertEqual((item["instructions"], item["hooks"]), ("ok", "ok"), item["tool"])


if __name__ == "__main__":
    unittest.main()
