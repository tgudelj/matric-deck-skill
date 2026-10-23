"""Offline DCS authoring acceptance tests using independently created synthetic definitions."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills/matric-decks"
sys.path.insert(0, str(SKILL / "scripts"))
import dcs_bios as dcs

DEFINITIONS = SKILL / "assets/dcs-demo/SKILL_DEMO.json"


class DcsTests(unittest.TestCase):
    def setUp(self):
        self.catalog = dcs.load_definitions(DEFINITIONS)

    def test_serialized_action_names_match_catalog_and_allowed_events(self):
        for key, metadata in dcs.deck.CATALOG["actions"].items():
            self.assertEqual(key, metadata["template"]["ActionTypeName"])
        a = dcs.deck.action("ActionSetServerVariables", VariableName=dcs.MAILBOX)
        self.assertEqual(a["ActionTypeName"], "EXM.MatricPro.Actions.ActionSetServerVariable")
        for control in dcs.deck.CATALOG["controls"].values():
            for actions in control["events"].values():
                self.assertTrue(set(actions).issubset(dcs.deck.CATALOG["actions"]))

    def test_module_aliases_and_definition_provenance(self):
        catalog = dcs.load_definitions(DEFINITIONS.parent, "SKILL_AIRCRAFT")
        self.assertIn("SKILL_DEMO", catalog["modules"])
        self.assertIn("MetadataStart", catalog["modules"])
        self.assertEqual(dcs.find_control(catalog, "_ACFT_NAME")["matric_variable"], "dcs__ACFT_NAME")
        self.assertTrue(all(len(p["sha256"]) == 64 for p in catalog["definitions"]))
        result = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/dcs_bios.py"), "inventory", str(DEFINITIONS.parent), "--aircraft", "SKILL_AIRCRAFT", "--module", "SKILL_DEMO"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(all(c["module"] == "SKILL_DEMO" for c in json.loads(result.stdout)["controls"]))
        with self.assertRaises(ValueError):
            dcs.load_definitions(DEFINITIONS.parent, "../missing")
        with self.assertRaises(ValueError):
            dcs.load_definitions(DEFINITIONS, "WRONG_AIRCRAFT")
        with self.assertRaises(ValueError):
            dcs.find_control(catalog, "INVENTED_CONTROL")
        ambiguous = copy.deepcopy(catalog)
        ambiguous["controls"].append(copy.deepcopy(ambiguous["controls"][0]))
        with self.assertRaises(ValueError):
            dcs.find_control(ambiguous, ambiguous["controls"][0]["identifier"])

    def test_command_interfaces_and_one_command_boundary(self):
        cases = [("SYN_POWER", "0"), ("SYN_POWER", "1"), ("SYN_POWER", "TOGGLE"),
                 ("SYN_POWER", "INC"), ("SYN_POWER", "DEC"), ("SYN_DIMMER", "+3200"),
                 ("SYN_DIMMER", "-3200"), ("SYN_TEXT", "text with spaces")]
        for identifier, arg in cases:
            with self.subTest(identifier=identifier, arg=arg):
                control = dcs.find_control(self.catalog, identifier)
                self.assertEqual(dcs.command_text(control, arg), identifier + " " + arg)
        cases = [("SYN_POWER", "2"), ("SYN_POWER", "-1"), ("SYN_POWER", "TOGGLE\nOTHER 1"),
                 ("SYN_DIMMER", "+65536"), ("SYN_DIMMER", "+0"), ("SYN_TEST_LAMP", "1")]
        for identifier, arg in cases:
            with self.subTest(identifier=identifier, arg=arg), self.assertRaises(ValueError):
                dcs.command_text(dcs.find_control(self.catalog, identifier), arg)

    def test_feedback_output_and_scale_require_real_definitions(self):
        control = dcs.find_control(self.catalog, "SYN_DIMMER")
        action = dcs.scaled_action(control)
        self.assertIn("65535", action["VariableCalculateValueFunction"])
        self.assertEqual(action["VariableValue"], "")
        self.assertEqual(dcs.feedback(control, "state.value")["VariableName"], "dcs_SYN_DIMMER")
        for outputs in ([], control["outputs"] * 2):
            bad = dict(control, outputs=outputs)
            with self.assertRaises(ValueError):
                dcs.feedback(bad, "state.value")

    def test_example_round_trip_and_required_outputs(self):
        with tempfile.TemporaryDirectory(prefix="matric-dcs-") as temp:
            staged = Path(temp) / "example"
            self.assertFalse(dcs.example(staged)["errors"])
            value, files = dcs.deck.load_deck(staged)
            self.assertEqual(value["ReferencedUserVariables"][0]["Value"], "")
            package = Path(temp) / "example.deck"
            result = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/deck_tool.py"), "pack", str(staged), "--output", str(package)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            value, files = dcs.deck.load_deck(package)
            report = dcs.audit(value, files, self.catalog)
            self.assertEqual(report["errors"], [])
            self.assertEqual(report["command_actions"], 5)
            self.assertEqual(set(report["required_outputs_by_module"]["SKILL_DEMO"]), {"SYN_DIMMER", "SYN_POWER", "SYN_READOUT", "SYN_TEST_LAMP"})
            self.assertTrue(report["warnings"])  # JavaScript remains deliberately unevaluated.

    def test_audit_catches_missing_mailbox_bad_commands_and_feedback(self):
        with tempfile.TemporaryDirectory(prefix="matric-dcs-") as temp:
            staged = Path(temp) / "example"
            dcs.example(staged)
            value, files = dcs.deck.load_deck(staged)
        for edit in (
                lambda v: v.update(ReferencedUserVariables=[]),
                lambda v: v["ReferencedUserVariables"][0].update(Value="SYN_POWER 1"),
                lambda v: v["Pages"][0]["Controls"][0]["ControlEvents"][0]["Actions"][0].update(VariableCalculateValueFunction=12),
                lambda v: v["Pages"][0]["Controls"][0]["ControlEvents"][0]["Actions"][0].update(VariableValue="SYN_POWER 9"),
                lambda v: v["Pages"][0]["Controls"][0]["Config"]["ControlBindings"][0].update(VariableName="dcs_INVENTED")):
            invalid = copy.deepcopy(value)
            edit(invalid)
            self.assertTrue(dcs.audit(invalid, files, self.catalog)["errors"])
        value["ReferencedUserVariables"].append({"Name": "COMBINED", "CalculateValueFunction": "return variables['dcs_SYN_READOUT'] + variables[\"dcs_SYN_TEST_LAMP\"];"})
        self.assertEqual(dcs.audit(value, files, self.catalog)["errors"], [])
        self.assertIn("dcs_SYN_READOUT", dcs.audit(value, files, self.catalog)["telemetry_variables"])


if __name__ == "__main__":
    unittest.main()
