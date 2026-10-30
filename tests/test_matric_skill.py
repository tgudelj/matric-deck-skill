"""Offline acceptance checks for the portable MATRIC authoring skill; no actions are executed."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills/matric-decks"


def module(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


deck_tool = module("deck_tool")
obs = module("obs_inventory")


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.deck, self.files = deck_tool.load_deck(SKILL / "assets/starter")

    def test_starter_and_archive_round_trip(self):
        self.assertEqual(deck_tool.validate(self.deck, self.files), {"errors": [], "warnings": []})
        with tempfile.TemporaryDirectory(prefix="matric-skill-test-") as temp:
            package, unpacked = Path(temp) / "Starter.deck", Path(temp) / "unpacked"
            self.cli("pack", SKILL / "assets/starter", "--output", package)
            with zipfile.ZipFile(package) as archive:
                self.assertTrue(all(n.startswith(self.deck["Id"] + "/") for n in archive.namelist()))
            self.cli("unpack", package, "--output", unpacked)
            self.assertEqual(deck_tool.load_deck(unpacked), (self.deck, self.files))
            self.assertNotEqual(self.cli("pack", unpacked, "--output", package, success=False).returncode, 0)
            self.assertNotEqual(self.cli("pack", unpacked, "--output", unpacked / "nested.deck", success=False).returncode, 0)

    def cli(self, *args, success=True):
        result = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/deck_tool.py"), *map(str, args)], capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_new_draft(self):
        with tempfile.TemporaryDirectory(prefix="matric-skill-test-") as temp:
            draft = Path(temp) / "draft"
            self.cli("new", "--title", "Unicode Å¾ scene", "--cols", 5, "--rows", 3, "--output", draft)
            deck, files = deck_tool.load_deck(draft)
            self.assertEqual(deck["Pages"][0]["Cols"], 5)
            self.assertFalse(deck_tool.validate(deck, files)["errors"])

    def test_deck_assets_must_be_flat(self):
        for separator in ("/", "\\"):
            with self.subTest(separator=separator):
                nested = "images" + separator + "panel.svg"
                deck = copy.deepcopy(self.deck)
                deck["Pages"][0]["BackgroundImage"] = nested
                report = deck_tool.validate(deck, {**self.files, nested: b"<svg/>"})
                self.assertTrue(any("Nested deck asset" in e for e in report["errors"]))
                self.assertTrue(any("without subfolders" in e for e in report["errors"]))
        # A nested reference is invalid even when its target file is absent.
        deck["Pages"][0]["BackgroundImage"] = "images/missing.svg"
        self.assertTrue(any("without subfolders" in e for e in deck_tool.validate(deck, self.files)["errors"]))

    def test_nested_deck_folder_cannot_be_validated_or_packaged(self):
        with tempfile.TemporaryDirectory(prefix="matric-flat-test-") as temp:
            draft = Path(temp) / "draft"
            draft.mkdir()
            for name, content in self.files.items():
                (draft / name).write_bytes(content)
            nested = draft / "images"
            nested.mkdir()
            package = Path(temp) / "bad.deck"
            for populated in (False, True):
                if populated:
                    (nested / "unused.svg").write_bytes(b"<svg/>")
                for verb, extra in (("validate", []), ("pack", ["--output", package])):
                    result = self.cli(verb, draft, *extra, success=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("subfolders are not allowed", result.stderr)
                self.assertFalse(package.exists())

    def test_nested_archive_entries_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="matric-flat-archive-test-") as temp:
            for entry in ("images/unused.svg", "images\\unused.svg", "images/"):
                package = Path(temp) / "nested.deck"
                with zipfile.ZipFile(package, "w") as archive:
                    for name, content in self.files.items():
                        archive.writestr(self.deck["Id"] + "/" + name, content)
                    archive.writestr(self.deck["Id"] + "/" + entry, b"")
                with self.assertRaisesRegex(ValueError, "subfolders are not allowed"):
                    deck_tool.load_deck(package)

    def test_page_grid_supported_boundaries(self):
        draft = copy.deepcopy(self.deck)
        draft["Pages"] = draft["Pages"][:1]
        page = draft["Pages"][0]
        page["Controls"] = []
        for cols, rows in ((1, 1), (50, 50), (1, 50), (50, 1)):
            with self.subTest(cols=cols, rows=rows):
                page.update(Cols=cols, Rows=rows)
                self.assertEqual(deck_tool.validate(draft, self.files)["errors"], [])
        for cols, rows in ((51, 50), (50, 51), (51, 51), (0, 10), (10, -1), (True, 10), (50.0, 10)):
            with self.subTest(cols=cols, rows=rows):
                page.update(Cols=cols, Rows=rows)
                self.assertTrue(any("Cols and Rows" in error for error in deck_tool.validate(draft, self.files)["errors"]))

    def test_new_cli_rejects_unsupported_grid_before_writing(self):
        with tempfile.TemporaryDirectory(prefix="matric-grid-test-") as temp:
            for cols, rows in ((51, 50), (50, 51), (0, 5), (5, -1)):
                draft = Path(temp) / f"bad-{cols}-{rows}"
                result = self.cli("new", "--title", "Grid bounds", "--cols", cols, "--rows", rows, "--output", draft, success=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(draft.exists())
            draft = Path(temp) / "supported"
            self.cli("new", "--title", "Largest supported grid", "--cols", 50, "--rows", 50, "--output", draft)
            deck, files = deck_tool.load_deck(draft)
            self.assertEqual(deck_tool.validate(deck, files)["errors"], [])

    def test_pack_rejects_oversized_saved_page(self):
        with tempfile.TemporaryDirectory(prefix="matric-oversized-test-") as temp:
            draft, package = Path(temp) / "draft", Path(temp) / "oversized.deck"
            self.cli("new", "--title", "Synthetic oversized page", "--cols", 50, "--rows", 50, "--output", draft)
            source = draft / "deck2.json"
            deck = json.loads(source.read_text(encoding="utf-8"))
            deck["Pages"][0]["Rows"] = 51
            source.write_text(json.dumps(deck), encoding="utf-8")
            self.assertNotEqual(self.cli("validate", draft, success=False).returncode, 0)
            self.assertNotEqual(self.cli("pack", draft, "--output", package, success=False).returncode, 0)
            self.assertFalse(package.exists())
            self.assertEqual(json.loads(source.read_text(encoding="utf-8"))["Pages"][0]["Rows"], 51)

    def test_new_controls_follow_their_definitions(self):
        for kind in deck_tool.CATALOG["controls"]:
            with self.subTest(control=kind):
                deck = copy.deepcopy(self.deck)
                deck["Pages"] = deck["Pages"][:1]
                deck["Pages"][0]["Controls"] = [deck_tool.new_control(kind, "Example", 0, 0, 2, 2)]
                self.assertEqual(deck_tool.validate(deck, self.files)["errors"], [])

    def test_catches_authoring_mistakes(self):
        cases = [
            lambda d: d["Pages"][0]["Controls"][0].update(X=99),
            lambda d: d["Pages"][0]["Controls"][1].update(Id=d["Pages"][0]["Controls"][0]["Id"]),
            lambda d: d.update(DefaultPageId="missing"),
            lambda d: d["Pages"][0].update(BackgroundImage="missing.png"),
            lambda d: d["Pages"][0]["Controls"][0]["Config"].update(ImaginarySetting=True),
            lambda d: d["Pages"][0]["Controls"][0]["ControlEvents"][0].update(Name="change"),
            lambda d: d["Pages"][0]["Controls"][0]["ControlEvents"][0]["Actions"][0].update(Modifiers=["invented"]),
        ]
        for index, change in enumerate(cases):
            with self.subTest(case=index):
                deck = copy.deepcopy(self.deck)
                change(deck)
                self.assertTrue(deck_tool.validate(deck, self.files)["errors"])
        slider = deck_tool.new_control("MCSlider", "Volume", 0, 2, 3)
        slider["ControlEvents"] = [{"Name": "valuechange", "Actions": [deck_tool.action("ActionHotkey", KeyCode=65)]}]
        self.deck["Pages"][0]["Controls"].append(slider)
        self.assertTrue(deck_tool.validate(self.deck, self.files)["errors"])

    def test_invalid_enum_and_overlap(self):
        button = self.deck["Pages"][0]["Controls"][0]
        button["ControlEvents"] = [{"Name": "release", "Actions": [deck_tool.action("ActionMixerMute", Command="unknown")]}]
        self.assertTrue(deck_tool.validate(self.deck, self.files)["errors"])
        button["ControlEvents"] = []
        other = self.deck["Pages"][0]["Controls"][1]
        other.update(X=button["X"], Y=button["Y"])
        self.assertTrue(deck_tool.validate(self.deck, self.files)["warnings"])

    def test_native_resources_and_opaque_applet_parameters(self):
        control = deck_tool.new_control("MCCustom", "Applet", 0, 2, 2)
        control["Config"]["AppletParams"] = {"Image": "https://example.invalid/image"}
        self.deck["Pages"][0]["Controls"].append(control)
        self.assertEqual(deck_tool.validate(self.deck, self.files)["errors"], [])
        kind = next(k for k, v in deck_tool.CATALOG["controls"].items() if "SwitchStateImages" in v["template"]["Config"])
        control = deck_tool.new_control(kind, "Switch", 2, 2, 2)
        control["Config"]["SwitchStateImages"] = ["missing.png"]
        self.deck["Pages"][0]["Controls"].append(control)
        self.assertTrue(any("missing resource missing.png" in e for e in deck_tool.validate(self.deck, self.files)["errors"]))

    def test_unsafe_archives_and_duplicate_json(self):
        with tempfile.TemporaryDirectory(prefix="matric-skill-test-") as temp:
            for name in ("../outside", "id/../../outside", "id/CON", "id/a:stream"):
                with self.subTest(name=name):
                    package = Path(temp) / "bad.deck"
                    with zipfile.ZipFile(package, "w") as archive:
                        archive.writestr(name, b"x")
                    with self.assertRaises(ValueError):
                        deck_tool.load_deck(package)
        with self.assertRaises(ValueError):
            deck_tool.read_json(b'{"Id":"a","Id":"b"}')

    def test_obs_nested_scene_and_global_audio(self):
        fixture = {"name": "Broadcast Å¾", "current_scene": "Main", "scene_order": [{"name": "Main"}],
                   "sources": [
                       {"name": "Main", "id": "scene", "uuid": "scene", "settings": {"items": [
                           {"name": "old name", "source_uuid": "group", "id": 7, "visible": True},
                           {"name": "Nested", "id": 8}, {"name": "missing", "id": 9}]}},
                       {"name": "Nested", "id": "scene", "settings": {"items": [{"name": "Camera", "id": 2}]}},
                       {"name": "Camera", "id": "browser_source", "uuid": "camera", "settings": {"url": "SECRET_URL"},
                        "filters": [{"name": "Crop", "id": "crop_filter"}], "hotkeys": {"toggle": [{"key": "OBS_KEY_A", "control": True}]}}],
                   "groups": [{"name": "Overlay", "uuid": "group", "id": "group", "settings": {"items": [{"source_uuid": "camera", "id": 3}]}}],
                   "AuxAudioDevice1": {"name": "Microphone", "id": "wasapi_input_capture", "muted": True, "volume": 0.5}}
        with tempfile.TemporaryDirectory(prefix="matric-obs-test-") as temp:
            path = Path(temp) / "collection.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            before = path.read_bytes()
            result = obs.inventory(path)
            self.assertEqual(path.read_bytes(), before)
        self.assertFalse(result["live"])
        self.assertEqual(result["collection"], "Broadcast Å¾")
        self.assertEqual(result["containers"][0]["items"][0]["name"], "Overlay")
        self.assertEqual(result["containers"][-1]["items"][0]["name"], "Camera")
        self.assertTrue(result["warnings"])
        self.assertEqual(result["sources"][-1]["saved_muted"], True)
        self.assertEqual(result["sources"][2]["hotkeys"]["toggle"][0]["key"], "OBS_KEY_A")
        self.assertNotIn("SECRET_URL", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
