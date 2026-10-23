import json
from pathlib import Path

from afc.session_dirs import GrantError, grant_dirs
from tests.helpers import AfcTestCase


class GrantDirsTest(AfcTestCase):
    def setUp(self):
        super().setUp()
        self.root = self.tmp / "root"
        self.root.mkdir()
        self.settings = self.root / ".claude" / "settings.local.json"

    def test_creates_file_when_absent_and_resolves_dirs(self):
        app = self.tmp / "app"
        app.mkdir()
        granted = grant_dirs(self.root, [app])
        self.assertEqual(granted, [str(app.resolve())])
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(data, {"permissions": {"additionalDirectories": [str(app.resolve())]},
                                "afcGranted": [str(app.resolve())]})

    def test_preserves_other_keys_and_dedupes(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text(
            json.dumps(
                {
                    "model": "x",
                    "permissions": {
                        "allow": ["Bash(ls)"],
                        "additionalDirectories": ["/existing", "/dup"],
                    },
                }
            ),
            encoding="utf-8",
        )
        app = self.tmp / "app"
        app.mkdir()
        granted = grant_dirs(self.root, [Path("/dup"), app])
        self.assertEqual(granted, ["/existing", "/dup", str(app.resolve())])
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(data["model"], "x")
        self.assertEqual(data["permissions"]["allow"], ["Bash(ls)"])
        self.assertEqual(data["permissions"]["additionalDirectories"], granted)

    def test_new_grant_replaces_earlier_flight_control_grants(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text(json.dumps(
            {"permissions": {"additionalDirectories": ["/mine"]}}), encoding="utf-8")
        a, b = self.tmp / "a", self.tmp / "b"
        a.mkdir()
        b.mkdir()
        grant_dirs(self.root, [a, a / "ws"])
        granted = grant_dirs(self.root, [b])
        self.assertEqual(granted, ["/mine", str(b.resolve())])
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(data["afcGranted"], [str(b.resolve())])

    def test_granting_twice_adds_nothing_new(self):
        app = self.tmp / "app"
        app.mkdir()
        first = grant_dirs(self.root, [app])
        second = grant_dirs(self.root, [app])
        self.assertEqual(first, second)

    def test_unreadable_settings_raise_and_stay_untouched(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text("{not json", encoding="utf-8")
        with self.assertRaises(GrantError):
            grant_dirs(self.root, [self.tmp])
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{not json")

    def test_non_object_settings_raise(self):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text("[]", encoding="utf-8")
        with self.assertRaises(GrantError):
            grant_dirs(self.root, [self.tmp])
