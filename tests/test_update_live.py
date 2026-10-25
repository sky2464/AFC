"""Tests for FC-026 slice 3: a real update between two copies, in scratch folders only."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from tests.helpers import AfcTestCase, git

REPO = Path(__file__).resolve().parent.parent


def snapshot(path: Path) -> tuple[int, float]:
    """File count and newest modified time under path (0, 0.0 when it does not exist)."""
    count, newest = 0, 0.0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                newest = max(newest, os.lstat(os.path.join(root, name)).st_mtime)
            except OSError:
                continue
            count += 1
    return count, newest


class UpdateLiveTest(AfcTestCase):
    offline_updates = False

    def afc(self, cwd, *args):
        # a scratch HOME, so the check sees a clean machine and not this one's installed add-ons
        fake_home = self.tmp / "home"
        fake_home.mkdir(exist_ok=True)
        env = dict(os.environ, AFC_HOME=str(self.home), HOME=str(fake_home), GIT_TERMINAL_PROMPT="0")
        env.pop("CLAUDE_PROJECT_DIR", None)
        done = subprocess.run(["sh", "bin/afc", *args], cwd=cwd, capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, timeout=120)
        return json.loads(done.stdout)

    def build(self):
        work = self.tmp / "work"
        work.mkdir()
        archive = subprocess.run(["git", "archive", "HEAD"], cwd=REPO, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(work)], input=archive, check=True)
        git(work, "init", "-q")
        (work / "VERSION").write_text("v0.03a\n")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "release v0.03a")
        git(work, "tag", "-a", "v0.03a", "-m", "older")
        (work / "VERSION").write_text("v0.03b\n")
        git(work, "commit", "-qam", "release v0.03b")
        git(work, "tag", "-a", "v0.03b", "-m", "newer")
        origin = self.tmp / "origin.git"
        git(self.tmp, "clone", "-q", "--bare", str(work), str(origin))
        copy = self.tmp / "copy"
        git(self.tmp, "clone", "-q", str(origin), str(copy))
        git(copy, "reset", "-q", "--hard", "v0.03a")
        return copy

    def test_update_from_older_tag_to_newer_tag(self):
        real = Path.home() / ".A-FC"
        before = snapshot(real)
        copy = self.build()
        self.assertEqual(self.afc(copy, "version")["version"], "v0.03a")
        result = self.afc(copy, "update")
        self.assertTrue(result["updated"], result)
        self.assertEqual(result["to"], "v0.03b")
        self.assertEqual(self.afc(copy, "version")["version"], "v0.03b")
        check = self.afc(copy, "check")
        self.assertEqual(check.get("problems"), [], check)
        self.assertEqual(snapshot(real), before)
