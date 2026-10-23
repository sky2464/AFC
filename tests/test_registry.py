import json
import unittest
from unittest import mock

from afc.registry import (
    Project,
    Registry,
    RegistryError,
    load_registry,
    save_registry,
    validate_name,
)
from tests.helpers import AfcTestCase


class ValidateNameTest(unittest.TestCase):
    def test_invalid_names_rejected(self):
        for bad in ["../x", "My App", "a", "x" * 64, "-lead", "kong_lab"]:
            with self.subTest(name=bad):
                with self.assertRaises(RegistryError):
                    validate_name(bad)

    def test_valid_name_returned(self):
        self.assertEqual(validate_name("kong-gateway-lab"), "kong-gateway-lab")
        self.assertEqual(validate_name("ab"), "ab")
        self.assertEqual(validate_name("x" * 63), "x" * 63)


class RegistryTest(AfcTestCase):
    def test_round_trip_and_active(self):
        reg = load_registry(self.home)
        reg.add(Project("kong-gateway-lab", "/c/k", "/w/k"))
        reg.set_active("kong-gateway-lab")
        save_registry(self.home, reg)
        again = load_registry(self.home)
        self.assertEqual(again.active().code_path, "/c/k")
        self.assertIn("kong-gateway-lab", (self.home / "projects.md").read_text())

    def test_save_leaves_only_registry_files(self):
        reg = Registry()
        reg.add(Project("kong-gateway-lab", "/c/k", "/w/k"))
        save_registry(self.home, reg)
        self.assertEqual(
            sorted(p.name for p in self.home.iterdir()),
            ["projects.json", "projects.md"],
        )

    def test_missing_registry_loads_empty(self):
        reg = load_registry(self.home)
        self.assertEqual(reg.projects, {})
        self.assertIsNone(reg.active_name)
        self.assertIsNone(reg.active())

    def test_duplicate_add_rejected(self):
        reg = Registry()
        reg.add(Project("kong-gateway-lab", "/c/k", "/w/k"))
        with self.assertRaises(RegistryError):
            reg.add(Project("kong-gateway-lab", "/c/other", "/w/other"))

    def test_get_returns_project_or_none(self):
        reg = Registry()
        reg.add(Project("kong-gateway-lab", "/c/k", "/w/k"))
        self.assertEqual(reg.get("kong-gateway-lab").workspace_path, "/w/k")
        self.assertIsNone(reg.get("missing"))

    def test_set_active_unknown_rejected(self):
        reg = Registry()
        with self.assertRaises(RegistryError):
            reg.set_active("missing")

    def test_update_changes_fields(self):
        reg = Registry()
        reg.add(Project("kong-gateway-lab", "/c/k", "/w/k"))
        updated = reg.update("kong-gateway-lab", status="paused", last_slice="3")
        self.assertEqual(updated.status, "paused")
        self.assertEqual(reg.get("kong-gateway-lab").last_slice, "3")

    def test_update_rejects_unknown_field(self):
        reg = Registry()
        reg.add(Project("kong-gateway-lab", "/c/k", "/w/k"))
        with self.assertRaises(RegistryError):
            reg.update("kong-gateway-lab", colour="blue")

    def test_update_rejects_name_change(self):
        reg = Registry()
        reg.add(Project("kong-gateway-lab", "/c/k", "/w/k"))
        with self.assertRaises(RegistryError):
            reg.update("kong-gateway-lab", name="other")

    def test_update_rejects_unknown_project(self):
        reg = Registry()
        with self.assertRaises(RegistryError):
            reg.update("missing", status="paused")

    def test_corrupt_registry_raises_clear_error(self):
        (self.home / "projects.json").write_text("{not json")
        with self.assertRaisesRegex(RegistryError, "^projects.json is unreadable"):
            load_registry(self.home)

    def test_wrong_shape_raises_clear_error(self):
        (self.home / "projects.json").write_text(json.dumps([1, 2]))
        with self.assertRaisesRegex(RegistryError, "^projects.json is unreadable"):
            load_registry(self.home)

    def test_unknown_project_key_raises_clear_error(self):
        data = {"active": None, "projects": [{"name": "kong-gateway-lab", "bogus": 1}]}
        (self.home / "projects.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(RegistryError, "^projects.json is unreadable"):
            load_registry(self.home)


    def _write(self, active, names):
        entries = [{"name": n, "code_path": "/c", "workspace_path": "/w"} for n in names]
        (self.home / "projects.json").write_text(json.dumps({"active": active, "projects": entries}))

    def test_duplicate_and_bad_names_rejected_on_load(self):
        for names in (["ab", "ab"], ["../x"]):
            self._write(None, names)
            with self.assertRaises(RegistryError, msg=names):
                load_registry(self.home)

    def test_add_validates_name(self):
        with self.assertRaises(RegistryError):
            Registry().add(Project(name="../x", code_path="/c", workspace_path="/w"))

    def test_dangling_active_loads_as_none(self):
        self._write("gone", ["ab"])
        reg = load_registry(self.home)
        self.assertIsNone(reg.active_name)
        reg.active_name = "gone"
        save_registry(self.home, reg)
        self.assertIn("Active: none", (self.home / "projects.md").read_text())

    def test_failed_md_write_leaves_json_unchanged(self):
        save_registry(self.home, Registry())
        reg = Registry()
        reg.add(Project(name="ab", code_path="/c", workspace_path="/w"))
        real = __import__("afc.registry", fromlist=["_atomic_write"])._atomic_write

        def fail_md(path, text):
            if path.name == "projects.md":
                raise OSError("disk full")
            real(path, text)

        with mock.patch("afc.registry._atomic_write", side_effect=fail_md):
            with self.assertRaises(OSError):
                save_registry(self.home, reg)
        self.assertEqual(load_registry(self.home).projects, {})


if __name__ == "__main__":
    unittest.main()
