"""Synthetic simulator mapping tests; no games, drivers or input are operated."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/matric-decks/scripts"
sys.path.insert(0, str(SCRIPTS))
import game_bindings as games
import deck_tool


ELITE = '''<Root PresetName="Synthetic" MajorVersion="4" MinorVersion="2">
<KeyboardLayout>en-US</KeyboardLayout>
<LandingGearToggle><Primary Device="Keyboard" Key="Key_G"><Modifier Device="Keyboard" Key="Key_LeftShift"/></Primary>
<Secondary Device="VIRTUAL-A" Key="Joy_3"/><ToggleOn Value="1"/></LandingGearToggle>
<ThrottleAxis><Binding Device="VIRTUAL-A" Key="Joy_ZAxis"/><Inverted Value="1"/><Deadzone Value="0.05"/></ThrottleAxis>
<Unassigned><Primary Device="{NoDevice}" Key=""/></Unassigned>
<ForeignChord><Primary Device="Keyboard" Key="Key_X"><Modifier Device="PHYSICAL" Key="Joy_1"/></Primary></ForeignChord>
</Root>'''
SC = '''<ActionMaps><ActionProfiles rebindVersion="2" profileName="test">
<options type="joystick" instance="2" Product="Synthetic vJoy"/>
<actionmap name="spaceship"><action name="gear"><rebind input="kb1_lalt+g" multiTap="2"/></action>
<action name="unbound"><rebind input="js2_ "/></action>
<action name="throttle"><rebind input="js2_z"/></action>
<action name="camera"><rebind input="js2_hat1_up"/></action>
<action name="odd"><rebind input="kb1_unknown+g"/></action>
</actionmap></ActionProfiles></ActionMaps>'''
MSFS = '''<?xml version="1.0"?><Version Num="1"/><FriendlyName>Test keyboard</FriendlyName>
<Device DeviceName="Keyboard" GUID="keyboard-guid"><AircraftInfo CategoryName="AIRPLANE"/>
<Context ContextName="AIRCRAFT"><Actions ActionName="KEY_FLAPS_INCR" Flag="34" Delay="0.25">
<Primary><KEY Information="G">71</KEY></Primary><Secondary><KEY>162</KEY><KEY>70</KEY></Secondary></Actions>
<Action ActionName="KEY_UNUSED" Flag="2"/></Context></Device>'''
DEVICES = {"VIRTUAL-A": {"DeviceId": 1, "buttons": 8, "axes": [50], "povs": 1,
                          "inputs": {"Joy_3": {"kind": "button", "button": 3},
                                     "Joy_ZAxis": {"kind": "axis", "axis": 50, "invert": True}}}}


class GameBindingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="matric-input-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def profile(self, text, name="profile.xml"):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_elite_alternatives_modifiers_axis_settings_and_unbound(self):
        path = self.profile(ELITE, "Synthetic.4.2.binds")
        report = games.inventory("elite", [path], DEVICES, ["NoSuchAction", "LandingGearToggle"])
        rows = report["bindings"]
        self.assertEqual(rows[0]["candidate"]["Modifiers"], ["LSHIFT"])
        self.assertEqual(rows[0]["candidate"]["KeyCode"], 71)
        self.assertEqual(rows[1]["candidate"]["ButtonId"], 3)
        self.assertTrue(rows[2]["candidate"]["InvertAxis"])
        self.assertEqual(rows[2]["settings"]["options"][1]["attributes"]["Value"], "0.05")
        self.assertTrue(rows[3]["unbound"])
        self.assertIsNone(rows[4]["candidate"])
        self.assertEqual(report["missing_actions"], ["NoSuchAction"])
        self.assertEqual(len(report["sources"][0]["sha256"]), 64)
        self.assertFalse(report["active_profiles_confirmed"])
        self.assertEqual(path.read_text(), ELITE)

    def test_sc_rebinds_preserve_multitap_and_explicit_clear(self):
        devices = {"js2": {"DeviceId": 1, "buttons": 8, "axes": [50], "povs": 1,
                            "inputs": {"z": {"kind": "axis", "axis": 50},
                                       "hat1_up": {"kind": "pov", "pov": 1, "direction": "N"}}}}
        report = games.inventory("starcitizen", [self.profile(SC)], devices)
        rows = report["bindings"]
        self.assertEqual(rows[0]["settings"]["rebind"]["multiTap"], "2")
        self.assertEqual(rows[0]["candidate"]["Modifiers"], ["LALT"])
        self.assertTrue(rows[1]["unbound"])
        self.assertEqual(rows[2]["candidate"]["Axis"], 50)
        self.assertEqual(rows[3]["candidate"]["POVDirection"], "N")
        self.assertIsNone(rows[4]["candidate"])
        self.assertTrue(any("omitted" in w for w in report["warnings"]))

    def test_msfs_fragments_action_variants_flags_and_wrapped_xml(self):
        for game in ("msfs2020", "msfs2024"):
            path = self.profile(MSFS)
            report = games.inventory(game, [path], active_confirmed=True)
            self.assertTrue(report["active_profiles_confirmed"])
            rows = report["bindings"]
            self.assertEqual(rows[0]["candidate"]["Modifiers"], ["LSHIFT"])
            self.assertEqual(rows[1]["candidate"]["Modifiers"], ["LCONTROL", "LSHIFT"])
            self.assertEqual(rows[0]["settings"]["action"]["Delay"], "0.25")
            self.assertTrue(rows[2]["unbound"])
        wrapped = '<DefaultInput>' + MSFS.split('?>')[1] + '</DefaultInput>'
        self.assertEqual(len(games.inventory("msfs2024", [self.profile(wrapped)])["bindings"]), 4)

    def test_physical_device_is_not_reassigned_and_msfs_numbers_are_not_keyboard(self):
        report = games.inventory("elite", [self.profile(ELITE)])
        self.assertIsNone(report["bindings"][1]["candidate"])
        data = MSFS.replace('DeviceName="Keyboard"', 'DeviceName="Physical HOTAS"')
        rows = games.inventory("msfs2024", [self.profile(data)])["bindings"]
        self.assertTrue(all(b["candidate"] is None for b in rows))

    def test_profile_selection_conflicts_and_missing_do_not_invent_defaults(self):
        first = self.profile(ELITE, "one.binds")
        second = self.profile(ELITE.replace("LandingGearToggle", "AnotherAction"), "two.binds")
        report = games.inventory("elite", [first, second])
        self.assertEqual(len(report["sources"]), 2)
        self.assertTrue(report["conflicts"])
        self.profile("Synthetic\nOtherPreset", "StartPreset.4.start")
        found = games.discover("elite", self.root)
        self.assertEqual(len(found["candidates"]), 3)
        self.assertEqual(next(c["selected_presets"] for c in found["candidates"] if "selected_presets" in c),
                         ["Synthetic", "OtherPreset"])

    def test_invalid_xml_and_device_capabilities_fail(self):
        for text in ('<!DOCTYPE Root [<!ENTITY x "x">]><Root/>', '<Root>', '<Wrong/>'):
            with self.assertRaises((ValueError, games.ET.ParseError)):
                games.inventory("elite", [self.profile(text)])
        for spec in ({"kind": "button", "button": 9}, {"kind": "axis", "axis": 48},
                     {"kind": "pov", "pov": 2, "direction": "N"},
                     {"kind": "pov", "pov": 1, "direction": "NE"}):
            devices = copy.deepcopy(DEVICES)
            devices["VIRTUAL-A"]["inputs"]["bad"] = spec
            with self.assertRaises(ValueError):
                games.validate_devices(devices)
        utf16 = self.root / "utf16.binds"
        utf16.write_bytes(ELITE.encode("utf-16"))
        self.assertTrue(games.inventory("elite", [utf16])["bindings"])

    def test_candidates_fit_catalog_and_validate_in_a_deck(self):
        report = games.inventory("elite", [self.profile(ELITE)], DEVICES)
        deck, _ = deck_tool.load_deck(SCRIPTS.parent / "assets/starter")
        deck["Pages"] = deck["Pages"][:1]
        deck["Pages"][0]["Controls"] = []
        for index, binding in enumerate(report["bindings"][:3]):
            candidate = binding["candidate"]
            axis = candidate["ActionTypeName"].endswith("ActionVJoyAxis")
            control = deck_tool.new_control("MCSlider" if axis else "MCButton", "Input", index, 0)
            event = "valuechange" if axis else "press"
            control["ControlEvents"] = [{"Name": event, "Actions": [candidate]}]
            deck["Pages"][0]["Controls"].append(control)
        deck["Pages"][0]["BackgroundImage"] = None
        self.assertEqual(deck_tool.validate(deck, set())["errors"], [])

    def test_unsupported_keyboard_codes_chords_and_vjoy_numbering(self):
        data = MSFS.replace('>71</KEY>', '>999</KEY>')
        self.assertIsNone(games.inventory("msfs2024", [self.profile(data)])["bindings"][0]["candidate"])
        data = SC.replace("kb1_lalt+g", "kb1_g+x")
        self.assertIsNone(games.inventory("starcitizen", [self.profile(data)])["bindings"][0]["candidate"])
        devices = copy.deepcopy(DEVICES)
        devices["VIRTUAL-A"]["inputs"]["Joy_1+Joy_2"] = {"kind": "button", "button": 3}
        chord = games.row("test", "chord", "Primary", "VIRTUAL-A", ["Joy_1+Joy_2"])
        self.assertIsNone(games.vjoy_candidate(chord, devices))
        for kind in ("button", "pov"):
            devices = copy.deepcopy(DEVICES)
            spec = {"kind": kind, kind: 0}
            if kind == "pov":
                spec["direction"] = "N"
            devices["VIRTUAL-A"]["inputs"]["invalid"] = spec
            with self.assertRaises(ValueError):
                games.validate_devices(devices)

    def test_discovery_accepts_only_game_profiles_and_size_is_bounded(self):
        self.profile(SC)
        self.profile('<unrelated private="not included"/>', 'other.xml')
        found = games.discover("starcitizen", self.root)
        self.assertEqual(len(found["candidates"]), 1)
        path = self.root / "oversized.xml"
        with path.open("wb") as stream:
            stream.truncate(games.MAX_BYTES + 1)
        with self.assertRaises(ValueError):
            games.read_xml(path)

    def test_cli_no_overwrite_and_input_read_only(self):
        path = self.profile(ELITE)
        output = self.root / "report.json"
        args = [sys.executable, "-B", str(SCRIPTS / "game_bindings.py"), "inventory",
                "--game", "elite", "--profile", str(path), "--output", str(output)]
        first = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(json.loads(output.read_text())["input_only"])
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
        self.assertEqual(path.read_text(), ELITE)


if __name__ == "__main__":
    unittest.main()
