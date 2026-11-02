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
XPLANE_KEYS = '''I
1005 version
# Synthetic assignments, not shipped X-Plane defaults
G <none> sim/synthetic/gear
G SHIFT+CTRL sim/synthetic/alternate_gear
Numpad-0 CTRL sim/synthetic/store_view
Space ALT synthetic/plugin/action
; <none> sim/synthetic/punctuation
KEY136 <none> sim/synthetic/unknown_key
P OPT sim/synthetic/mac_modifier
F2 META sim/synthetic/unknown_modifier
<none> <none> sim/synthetic/unassigned
G <none> sim/synthetic/conflict
'''
XPLANE_JOYSTICKS = '''I
1100 version
_joy_unique_id0 SYNTHETIC-PHYSICAL
_joy_AXIS_rev0 1
_joy_AXIS_min0 -1.000000
_joy_AXIS_curve0 0.2 0.7 1.0
_joy_BUTN_use0 sim/synthetic/gear
_joy_BUTN_use160 synthetic/plugin/action
_joy_BUTN_use161 sim/none/none
_joy_BUTN_use162
_joy_AXIS_use0 11
_joy_AXIS_use25 0
_joy_future_setting0 opaque value
'''
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

    def test_xplane_keys_modifiers_alternatives_plugins_and_conflicts(self):
        path = self.profile(XPLANE_KEYS, "X-Plane Keys.prf")
        report = games.inventory("xplane", [path], required=["sim/synthetic/gear", "missing"])
        rows = report["bindings"]
        self.assertEqual(rows[0]["action"], "sim/synthetic/gear")
        self.assertEqual(rows[0]["candidate"]["KeyCode"], 71)
        self.assertEqual(rows[0]["candidate"]["Modifiers"], [])
        self.assertEqual(rows[1]["candidate"]["Modifiers"], ["LSHIFT", "LCONTROL"])
        self.assertEqual(rows[1]["settings"]["modifier_token"], "SHIFT+CTRL")
        self.assertEqual(rows[2]["candidate"]["KeyCode"], 96)
        self.assertEqual(rows[3]["action"], "synthetic/plugin/action")
        self.assertEqual(rows[3]["candidate"]["Modifiers"], ["LALT"])
        self.assertTrue(all(b["candidate"] is None for b in rows[4:9]))
        self.assertTrue(rows[8]["unbound"])
        self.assertEqual(report["missing_actions"], ["missing"])
        self.assertEqual(len(report["conflicts"]), 1)
        self.assertEqual(report["conflicts"][0]["bindings"], [rows[0]["id"], rows[9]["id"]])
        self.assertEqual(len(report["sources"][0]["sha256"]), 64)
        self.assertEqual(path.read_text(), XPLANE_KEYS)

    def test_xplane_joystick_indices_axis_functions_and_settings_are_preserved(self):
        report = games.inventory("xplane", [self.profile(XPLANE_JOYSTICKS, "Trainer - Joysticks.prf")])
        rows = report["bindings"]
        self.assertEqual(rows[1]["inputs"], ["_joy_BUTN_use160"])
        self.assertEqual(rows[1]["device"], "xplane-joystick")
        self.assertEqual(rows[1]["settings"]["index"], 160)
        self.assertTrue(rows[2]["unbound"])
        self.assertTrue(rows[3]["unbound"])
        self.assertEqual(rows[4]["action"], "axis-use:11")
        self.assertEqual(rows[4]["settings"]["assignment"], "11")
        self.assertTrue(rows[5]["unbound"])
        self.assertTrue(all(b["candidate"] is None for b in rows))
        preferences = report["profiles"][0]["preferences"]
        self.assertIn("_joy_unique_id0 SYNTHETIC-PHYSICAL", [p["raw"] for p in preferences])
        self.assertIn("_joy_AXIS_curve0 0.2 0.7 1.0", [p["raw"] for p in preferences])
        self.assertIn("_joy_future_setting0 opaque value", [p["raw"] for p in preferences])
        self.assertTrue(rows[4]["warnings"])
        self.assertFalse(report["active_profiles_confirmed"])

    def test_xplane_vjoy_requires_explicit_global_input_correspondence(self):
        path = self.profile(XPLANE_JOYSTICKS, "X-Plane Joystick Settings.prf")
        devices = {"xplane-joystick": {"DeviceId": 2, "buttons": 8, "axes": [50], "povs": 0,
                   "inputs": {"_joy_BUTN_use160": {"kind": "button", "button": 3},
                              "_joy_AXIS_use0": {"kind": "axis", "axis": 50, "invert": True}}}}
        report = games.inventory("xplane", [path], devices)
        rows = report["bindings"]
        self.assertIsNone(rows[0]["candidate"])
        self.assertEqual(rows[1]["candidate"]["DeviceId"], 2)
        self.assertEqual(rows[1]["candidate"]["ButtonId"], 3)
        self.assertEqual(rows[4]["candidate"]["Axis"], 50)
        self.assertTrue(rows[4]["candidate"]["InvertAxis"])
        devices["xplane-joystick"]["inputs"]["_joy_AXIS_use25"] = {"kind": "axis", "axis": 50}
        self.assertIsNone(games.inventory("xplane", [path], devices)["bindings"][5]["candidate"])
        other = self.profile(XPLANE_JOYSTICKS, "Other - Joysticks.prf")
        with self.assertRaisesRegex(ValueError, "one selected joystick profile"):
            games.inventory("xplane", [path, other], devices)

    def test_xplane_discovery_finds_global_and_named_pairs_without_selecting(self):
        self.profile(XPLANE_KEYS, "X-Plane Keys.prf")
        self.profile(XPLANE_JOYSTICKS, "X-Plane Joystick Settings.prf")
        profiles = self.root / "control profiles"
        profiles.mkdir()
        (profiles / "Trainer - Keys.prf").write_text(XPLANE_KEYS, encoding="utf-8")
        (profiles / "Trainer - Joysticks.prf").write_text(XPLANE_JOYSTICKS, encoding="utf-8")
        self.profile(XPLANE_KEYS, "Plane Maker Keys.prf")
        self.profile(XPLANE_KEYS, "X-Plane.prf")
        self.profile('I\n1100 version\nJOY\nOS: Windows', "default.joy")
        self.profile('<Root/>', "Unrelated - Keys.prf")
        found = games.discover("xplane", self.root)
        self.assertEqual(len(found["candidates"]), 4)
        self.assertEqual({c["metadata"]["kind"] for c in found["candidates"]}, {"keyboard", "joystick"})
        paths = [Path(c["path"]) for c in found["candidates"]]
        report = games.inventory("xplane", paths, active_confirmed=True)
        self.assertEqual(len(report["profiles"]), 4)
        self.assertTrue(report["active_profiles_confirmed"])
        self.assertTrue(report["conflicts"])

    def test_xplane_unknown_lines_invalid_headers_and_oversize(self):
        path = self.profile(XPLANE_KEYS + "invalid assignment\n", "X-Plane Keys.prf")
        report = games.inventory("xplane", [path])
        self.assertEqual(report["profiles"][0]["unparsed_lines"][0]["raw"], "invalid assignment")
        self.assertTrue(report["profiles"][0]["warnings"])
        data = XPLANE_JOYSTICKS + "_joy_AXIS_use1 mystery\n_joy_BUTN_use2 ???\n_joy_BUTN_use_bad unknown\n_joy_BUTN_use3 sim/test unexpected\n"
        path = self.profile(data, "Trainer - Joysticks.prf")
        report = games.inventory("xplane", [path])
        self.assertEqual(len(report["profiles"][0]["unparsed_lines"]), 4)
        for data in ("", "I\nnot-a-version\nG <none> sim/test", "<Root/>", "I\n1005 version\ngarbage"):
            with self.assertRaises(ValueError):
                games.inventory("xplane", [self.profile(data, "renamed.prf")])
        path.write_bytes(b"\xff\x00")
        with self.assertRaises(UnicodeError):
            games.inventory("xplane", [path])
        with path.open("wb") as stream:
            stream.truncate(games.MAX_BYTES + 1)
        with self.assertRaises(ValueError):
            games.inventory("xplane", [path])

    def test_xplane_renamed_utf16_empty_profiles_and_keyboard_key_distinctions(self):
        path = self.root / "renamed.prf"
        path.write_bytes(XPLANE_KEYS.replace("I\n", "A\n", 1).encode("utf-16"))
        report = games.inventory("xplane", [path])
        self.assertEqual(report["profiles"][0]["platform_marker"], "A")
        empty = self.profile("I\n1005 version\n", "Empty - Keys.prf")
        self.assertEqual(games.inventory("xplane", [empty])["bindings"], [])
        self.assertEqual(len(games.discover("xplane", self.root)["candidates"]), 1)
        text = "I\n1005 version\n0 <none> sim/test/top\nNumpad-0 <none> sim/test/pad\nF1 <none> sim/test/fn\n"
        report = games.inventory("xplane", [self.profile(text, "Keys.prf")])
        self.assertEqual([b["candidate"]["KeyCode"] for b in report["bindings"]], [48, 96, 112])
        self.assertEqual(report["conflicts"], [])

    def test_xplane_cli_discovery_inventory_no_overwrite_and_portable_actions(self):
        path = self.profile(XPLANE_KEYS, "X-Plane Keys.prf")
        command = [sys.executable, "-B", str(SCRIPTS / "game_bindings.py")]
        found = subprocess.run(command + ["discover", "--game", "xplane", "--root", str(self.root)],
                               capture_output=True, text=True)
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertEqual(len(json.loads(found.stdout)["candidates"]), 1)
        output = self.root / "report.json"
        args = command + ["inventory", "--game", "xplane", "--profile", str(path), "--output", str(output)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
        self.assertEqual(path.read_text(), XPLANE_KEYS)
        deck, _ = deck_tool.load_deck(SCRIPTS.parent / "assets/starter")
        page = deck["Pages"][0]
        deck["Pages"] = [page]
        page["Controls"] = []
        page["BackgroundImage"] = None
        for index, binding in enumerate(json.loads(output.read_text())["bindings"][:4]):
            control = deck_tool.new_control("MCButton", "Synthetic", index, 0)
            control["ControlEvents"] = [{"Name": "press", "Actions": [binding["candidate"]]}]
            page["Controls"].append(control)
        self.assertEqual(deck_tool.validate(deck, set())["errors"], [])

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
