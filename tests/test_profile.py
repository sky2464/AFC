import unittest

from afc.profile import (
    ALL_MODULES,
    BASE_MODULES,
    PROFILES,
    TOUCH_MAP,
    Answers,
    classify,
    modules_for,
)


class ClassifyTest(unittest.TestCase):
    def test_kong_learning_is_personal(self):
        self.assertEqual(classify(Answers("learning", 1, "self", None, False)), "personal")

    def test_internal_200_users_is_enterprise(self):
        self.assertEqual(classify(Answers("work", 200, "internal", "Acme", False)), "enterprise")

    def test_small_internal_tool_is_work(self):
        self.assertEqual(classify(Answers("work", 10, "internal", "Acme", False)), "work")

    def test_sensitive_data_escalates(self):
        self.assertEqual(classify(Answers("work", 5, "internal", "Acme", True)), "enterprise")

    def test_product_without_company_is_mvp(self):
        self.assertEqual(classify(Answers("product", 1000, "external", None, False)), "mvp")

    def test_company_external_audience_is_enterprise(self):
        self.assertEqual(classify(Answers("work", 1, "both", "Acme", False)), "enterprise")

    def test_company_over_50_users_is_enterprise_even_internal(self):
        self.assertEqual(classify(Answers("mvp", 51, "internal", "Acme", False)), "enterprise")

    def test_company_with_50_users_is_not_escalated_by_size(self):
        self.assertEqual(classify(Answers("work", 50, "internal", "Acme", False)), "work")

    def test_company_work_without_escalators_is_work_even_for_mvp_purpose(self):
        self.assertEqual(classify(Answers("mvp", 10, "internal", "Acme", False)), "work")

    def test_prototype_is_prototype(self):
        self.assertEqual(classify(Answers("prototype", 3, "self", None, False)), "prototype")

    def test_personal_is_personal(self):
        self.assertEqual(classify(Answers("personal", 1, "self", None, False)), "personal")

    def test_external_users_without_company_but_personal_purpose_is_personal(self):
        self.assertEqual(classify(Answers("personal", 500, "external", None, False)), "personal")

    def test_sensitive_data_without_company_is_personal_not_enterprise(self):
        # Escalation only applies when a company is present.
        self.assertEqual(classify(Answers("learning", 1, "self", None, True)), "personal")


class ModulesForTest(unittest.TestCase):
    def test_personal_touching_auth(self):
        self.assertEqual(
            modules_for("personal", {"auth"}),
            ["secrets", "identity", "input", "ai-safety"],
        )

    def test_enterprise_gets_all(self):
        self.assertEqual(modules_for("enterprise", set()), list(ALL_MODULES))

    def test_result_follows_canonical_order(self):
        result = modules_for("personal", {"deps", "auth"})
        self.assertEqual(result, [m for m in ALL_MODULES if m in result])

    def test_unknown_touch_is_ignored(self):
        self.assertEqual(modules_for("personal", {"nonsense"}), modules_for("personal", set()))

    def test_unknown_profile_raises(self):
        with self.assertRaises(ValueError):
            modules_for("bogus", set())

    def test_touch_map_adds_expected_module(self):
        for touch, module in TOUCH_MAP.items():
            with self.subTest(touch=touch):
                self.assertIn(module, modules_for("personal", {touch}))


class ConstantsTest(unittest.TestCase):
    def test_profiles_order(self):
        self.assertEqual(PROFILES, ("personal", "prototype", "mvp", "work", "enterprise"))

    def test_all_modules_order(self):
        self.assertEqual(
            ALL_MODULES,
            (
                "secrets",
                "identity",
                "input",
                "api",
                "logging-pii",
                "dependencies",
                "containers-deploy",
                "data",
                "architecture",
                "ai-safety",
            ),
        )

    def test_base_modules_cover_every_profile(self):
        self.assertEqual(set(BASE_MODULES), set(PROFILES))

    def test_base_modules_are_cumulative(self):
        self.assertEqual(BASE_MODULES["personal"], ("secrets", "input", "ai-safety"))
        self.assertTrue(set(BASE_MODULES["personal"]) <= set(BASE_MODULES["prototype"]))
        self.assertTrue(set(BASE_MODULES["prototype"]) <= set(BASE_MODULES["mvp"]))
        self.assertTrue(set(BASE_MODULES["mvp"]) <= set(BASE_MODULES["work"]))
        self.assertIs(BASE_MODULES["work"], ALL_MODULES)
        self.assertEqual(set(BASE_MODULES["enterprise"]), set(ALL_MODULES))

    def test_touch_map_values(self):
        self.assertEqual(
            TOUCH_MAP,
            {
                "auth": "identity",
                "api": "api",
                "data": "data",
                "deploy": "containers-deploy",
                "logs": "logging-pii",
                "deps": "dependencies",
                "input": "input",
            },
        )


if __name__ == "__main__":
    unittest.main()
