"""Applet authoring checks against synthetic fixtures; no MATRIC actions execute."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

SKILL = Path(__file__).resolve().parents[1] / "skills/matric-decks"
sys.path.insert(0, str(SKILL / "scripts"))
import applet_tool as applets
import deck_tool as deck
import dcs_bios as dcs


class AppletTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((applets.TEMPLATE / "manifest.json").read_text(encoding="utf-8"))

    def test_manifest_casing_and_runtime_ids(self):
        raw = copy.deepcopy(self.raw)
        raw["AppletID"] = raw.pop("AppletId")
        result = applets.manifest(raw)
        self.assertEqual(result["AppletId"], self.raw["AppletId"])
        self.assertEqual(applets.runtime_action("ActionSetServerVariables"), "EXM.MatricPro.Actions.ActionSetServerVariable")
        self.assertEqual(applets.runtime_action("EXM.MatricPro.Actions.ActionOBS"), "EXM.MatricPro.Actions.ActionOBS")
        with self.assertRaisesRegex(ValueError, "runtime ActionId"):
            applets.runtime_action("ActionSetServerVariable")

    def test_invalid_manifest_shapes_and_names(self):
        cases = []
        for field, value in (("AppletId", "../escape"), ("AppletId", "CON"), ("DisplayName", ""),
                             ("VersionMajor", -1), ("VersionMinor", 0.5), ("VersionMinor", True),
                             ("AppletParams", {}), ("EventsDefinition", {})):
            case = copy.deepcopy(self.raw)
            case[field] = value
            cases.append(case)
        case = copy.deepcopy(self.raw)
        case["AppletID"] = "another"
        cases.append(case)
        case = copy.deepcopy(self.raw)
        case["AppletParams"].append(copy.deepcopy(case["AppletParams"][0]))
        cases.append(case)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                applets.manifest(case)

    def test_parameter_types_defaults_and_reserved_events(self):
        for field, value in (("ParamType", "boolean"), ("ListItems", {}), ("Default", 42)):
            case = copy.deepcopy(self.raw)
            case["AppletParams"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                applets.manifest(case)
        for event in ("reqvariables", "__cancel_applet_inputs", "select-release"):
            case = copy.deepcopy(self.raw)
            case["EventsDefinition"][0]["Name"] = event
            with self.assertRaises(ValueError):
                applets.manifest(case)
        case = copy.deepcopy(self.raw)
        next(parameter for parameter in case["AppletParams"] if parameter["ParamType"] == "list")["Default"] = "not-an-option"
        with self.assertRaises(ValueError):
            applets.manifest(case)

    def test_new_cli_and_missing_local_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "applet"
            result = subprocess.run([sys.executable, "-B", str(SKILL / "scripts/applet_tool.py"), "new",
                                     "--id", "synthetic-inspector", "--title", "Synthetic", "--output", str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(applets.validate(source)["warnings"], [])
            self.assertEqual(applets.load(source)[0]["AppletId"], "synthetic-inspector")
            with self.assertRaises(FileExistsError):
                applets.new(source, "same", "Same")
            (source / "history.js").unlink()
            with self.assertRaisesRegex(ValueError, "missing local resource"):
                applets.validate(source)

    def test_separate_mapl_package_reproducibility_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "applet"
            applets.new(source, "synthetic-inspector", "Synthetic")
            first, second = Path(temp) / "first.mapl", Path(temp) / "second.mapl"
            applets.pack(source, first)
            applets.pack(source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            data, files = applets.load(first)
            self.assertEqual(data["AppletId"], "synthetic-inspector")
            self.assertIn("bridge.js", files)
            self.assertEqual(applets.validate(first)["warnings"], [])
            with self.assertRaises(FileExistsError):
                applets.pack(source, first)
            with self.assertRaises(ValueError):
                applets.pack(source, source / "nested.mapl")
            with self.assertRaises(ValueError):
                applets.pack(source, Path(temp) / "wrong.deck")

    def test_wrapped_packages_and_unsafe_paths(self):
        metadata = json.dumps(self.raw).encode()
        with tempfile.TemporaryDirectory() as temp:
            def archive(name, entries):
                target = Path(temp) / name
                with zipfile.ZipFile(target, "w") as zipped:
                    for key, content in entries:
                        zipped.writestr(key, content)
                return target
            wrapped = archive("wrapped.mapl", [("folder/manifest.json", metadata), ("folder/applet.html", b"<html></html>")])
            self.assertEqual(set(applets.load(wrapped)[1]), {"manifest.json", "applet.html"})
            for i, bad in enumerate(("../escape", "C:/escape", "NUL.txt", "a/../../escape", "a/" * 17 + "deep")):
                target = archive(f"bad{i}.mapl", [("manifest.json", metadata), ("applet.html", b"html"), (bad, b"x")])
                with self.subTest(path=bad), self.assertRaises(ValueError):
                    applets.load(target)
            for i, entries in enumerate((
                [("manifest.json", metadata), ("applet.html", b"")],
                [("outer/inner/manifest.json", metadata), ("outer/inner/applet.html", b"html")],
                [("wrap/manifest.json", metadata), ("wrap/applet.html", b"html"), ("outside.txt", b"x")],
                [("manifest.json", metadata), ("applet.html", b"html"), ("APPLET.HTML", b"duplicate")],
                [("manifest.json", metadata), ("applet.html", b"html"), ("assets/manifest.json", metadata)],
                [("manifest.json", b'{"AppletId":"a","AppletId":"b"}'), ("applet.html", b"html")],
            )):
                with self.subTest(case=i), self.assertRaises(ValueError):
                    applets.load(archive(f"shape{i}.mapl", entries))

    def test_archive_size_metadata_and_symlink_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "applet"
            applets.new(source, "synthetic-inspector", "Synthetic")
            with mock.patch.object(applets, "MAX_BYTES", 30), self.assertRaises(ValueError):
                applets.load(source)
            with mock.patch.object(applets, "MAX_FILES", 2), self.assertRaises(ValueError):
                applets.load(source)
            target = Path(temp) / "linked.mapl"
            with zipfile.ZipFile(target, "w") as zipped:
                entry = zipfile.ZipInfo("link")
                entry.external_attr = 0o120777 << 16
                zipped.writestr(entry, "elsewhere")
            with self.assertRaisesRegex(ValueError, "Linked"):
                applets.load(target)
            (source / "manifest.json").write_bytes(b" " * (1024 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, "1 MiB"):
                applets.load(source)

    def test_external_resources_warn_and_font_files_are_not_bundled(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "applet"
            applets.new(source, "synthetic-inspector", "Synthetic")
            (source / "applet.html").write_text('<img src="https://example.invalid/art.png">', encoding="utf-8")
            self.assertTrue(applets.validate(source)["warnings"])
            (source / "font.woff2").write_bytes(b"synthetic-not-a-font")
            with self.assertRaisesRegex(ValueError, "Fonts"):
                applets.validate(source)

    def test_example_dynamic_events_and_parameter_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "example"
            applets.example(folder)
            value, files = deck.load_deck(folder / "History.deck")
            manifests = applets.load_manifests([folder / "History.mapl"])
            self.assertEqual(deck.validate(value, files, manifests), {"errors": [], "warnings": []})
            self.assertNotIn("manifest.json", files)  # .deck does not install the applet.
            self.assertTrue(deck.validate(value, files)["errors"])  # Dynamic events require metadata.
            self.assertTrue(deck.validate(value, files, {})["errors"])
            custom = value["Pages"][0]["Controls"][0]
            for params in ({"Unknown": 3}, {"FileResources": []}, {"SampleLimit": True}, {"Scale": "invalid"}, {"ShowValues": "false"}, []):
                custom["Config"]["AppletParams"] = params
                with self.subTest(params=params):
                    self.assertTrue(deck.validate(value, files, manifests)["errors"])
            custom["Config"]["AppletParams"] = {"SampleLimit": 20, "ShowValues": False, "Scale": "auto"}
            self.assertEqual(deck.validate(value, files, manifests)["errors"], [])
            custom["ControlEvents"][0]["Name"] = "made-up"
            self.assertTrue(deck.validate(value, files, manifests)["errors"])

    def test_manifest_action_allowlist_and_navigation_are_enforced(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "example"
            applets.example(folder)
            value, files = deck.load_deck(folder / "History.deck")
            manifests = applets.load_manifests([folder / "applet"])
            actions = value["Pages"][0]["Controls"][0]["ControlEvents"][0]["Actions"]
            actions[:] = [deck.action("ActionRunApp", AppPath="synthetic.exe")]
            self.assertTrue(any("incompatible action" in e for e in deck.validate(value, files, manifests)["errors"]))
            definition = next(iter(manifests.values()))
            definition["EventsDefinition"][0]["AllowedActions"] = ["ActionGoToPage"]
            actions[:] = [deck.action("ActionGoToPage", TargetPageId="missing")]
            self.assertTrue(any("TargetPageId" in e for e in deck.validate(value, files, manifests)["errors"]))

    def test_deck_cli_pack_and_validate_with_separate_applet(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "example"
            applets.example(folder)
            for command in ("validate", "pack"):
                args = [sys.executable, "-B", str(SKILL / "scripts/deck_tool.py"), command, str(folder / "deck"),
                        "--applet", str(folder / "History.mapl")]
                if command == "pack":
                    args += ["--output", str(folder / "Repacked.deck")]
                result = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            with self.assertRaisesRegex(ValueError, "Duplicate supplied"):
                applets.load_manifests([folder / "applet", folder / "History.mapl"])

    def test_dcs_applet_variable_parameters_are_audited(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "example"
            applets.example(folder)
            dcs.example(Path(temp) / "dcs")
            value, files = deck.load_deck(Path(temp) / "dcs")
            applet_deck, _ = deck.load_deck(folder / "History.deck")
            custom = applet_deck["Pages"][0]["Controls"][0]
            custom.update(X=4, Y=0, Width=2, Height=2)
            custom["Config"]["AppletParams"]["SignalVariable"] = "dcs_NONEXISTENT"
            value["Pages"][0]["Controls"].append(custom)
            manifests = applets.load_manifests([folder / "applet"])
            catalog = dcs.load_definitions(SKILL / "assets/dcs-demo/SKILL_DEMO.json")
            report = dcs.audit(value, files, catalog, manifests)
            self.assertTrue(any("NONEXISTENT" in error for error in report["errors"]))
            custom["Config"]["AppletParams"]["SignalVariable"] = "dcs_SYN_DIMMER"
            self.assertEqual(dcs.audit(value, files, catalog, manifests)["errors"], [])


if __name__ == "__main__":
    unittest.main()
