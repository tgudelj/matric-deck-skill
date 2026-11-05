"""Offline checks for declared calculation resources; no native actions execute."""
import copy
import importlib.util
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills/matric-decks"
spec = importlib.util.spec_from_file_location("resource_deck_tool", SKILL / "scripts/deck_tool.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class AdditionalResourceTests(unittest.TestCase):
    def setUp(self):
        self.deck, self.files = tool.load_deck(SKILL / "assets/additional-resources")
        self.control = self.deck["Pages"][0]["Controls"][0]

    def test_synthetic_example_and_case_sensitive_aliases(self):
        self.assertEqual(tool.validate(self.deck, self.files), {"errors": [], "warnings": []})
        self.control["Config"]["AdditionalResources"]["Live"] = "live.svg"
        self.assertFalse(tool.validate(self.deck, self.files)["errors"])
        for value in ({}, None):
            self.control["Config"]["AdditionalResources"] = value
            self.assertFalse(tool.validate(self.deck, self.files)["errors"])

    def test_missing_dynamic_file_rejected(self):
        files = {k: v for k, v in self.files.items() if k != "muted.svg"}
        errors = tool.validate(self.deck, files)["errors"]
        self.assertTrue(any("missing resource muted.svg" in error for error in errors))

    def test_invalid_maps_and_filename_values(self):
        for mapping in ([], "not a map", {"": "live.svg"}, {" ": "live.svg"}, {"x": False}, {"x": None},
                        {"x": ""}, {"x": "images/live.svg"}, {"x": "images\\live.svg"}, {"x": "../live.svg"},
                        {"x": "deck2.json"}, {"x": "deck.json"}, {"x": "CON.svg"}, {"x": "live.svg "}):
            with self.subTest(mapping=mapping):
                deck = copy.deepcopy(self.deck)
                deck["Pages"][0]["Controls"][0]["Config"]["AdditionalResources"] = mapping
                self.assertTrue(tool.validate(deck, self.files)["errors"])

    def test_dictionary_schema_retains_string_value_type(self):
        schema = tool.CATALOG["controls"]["MCButton"]["properties"]["AdditionalResources"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["additionalProperties"]["type"], "string")


if __name__ == "__main__":
    unittest.main()
