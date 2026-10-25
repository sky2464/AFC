"""Keep the Mac awake while building: awake on|off|status (FC-018 slice 4)."""

import os
import stat
import time
from pathlib import Path
from unittest import mock

from tests.helpers import AfcTestCase, run_cli


def fake(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class AwakeTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.log = self.tmp / "caffeinate.log"
        fake(self.bin, "caffeinate", f'echo "$@" >> "{self.log}"\nexec sleep 30')
        self.power = "Now drawing from 'AC Power'"
        fake(self.bin, "pmset", 'echo "$AFC_TEST_POWER"')
        env = {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
               "AFC_TEST_POWER": self.power}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("afc.cli_awake.is_macos", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(run_cli, ["awake", "off"])

    def starts(self):
        for _ in range(50):
            if self.log.exists():
                break
            time.sleep(0.05)
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_on_starts_it_once(self):
        code, out = run_cli(["awake", "on"])
        self.assertEqual(code, 0)
        self.assertTrue(out["awake"])
        code, out = run_cli(["awake", "on"])
        self.assertTrue(out["awake"])
        self.assertEqual(len(self.starts()), 1)

    def test_four_hour_limit_is_passed(self):
        run_cli(["awake", "on"])
        self.assertEqual(self.starts(), ["-i -t 14400"])

    def test_off_stops_it(self):
        _, on = run_cli(["awake", "on"])
        pid = on["pid"]
        _, out = run_cli(["awake", "off"])
        self.assertFalse(out["awake"])
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.05)
        else:
            self.fail("caffeinate still running after off")
        _, status = run_cli(["awake", "status"])
        self.assertFalse(status["awake"])

    def test_status_reports_battery(self):
        os.environ["AFC_TEST_POWER"] = "Now drawing from 'Battery Power'"
        _, out = run_cli(["awake", "status"])
        self.assertEqual(out, {"awake": False, "on_battery": True})
        os.environ["AFC_TEST_POWER"] = self.power
        run_cli(["awake", "on"])
        _, out = run_cli(["awake", "status"])
        self.assertTrue(out["awake"])
        self.assertFalse(out["on_battery"])

    def test_other_systems_get_not_macos(self):
        with mock.patch("afc.cli_awake.is_macos", return_value=False):
            for state in ("on", "status", "off"):
                code, out = run_cli(["awake", state])
                self.assertEqual(code, 0)
                self.assertEqual(out, {"awake": False, "reason": "not macOS"})
        self.assertEqual(self.starts(), [])
