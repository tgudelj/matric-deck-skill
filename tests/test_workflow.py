"""Synthetic setup, handover and revision tests; no applications or actions are operated."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/matric-decks/scripts"
sys.path.insert(0, str(SCRIPTS))
import deck_tool
import dcs_bios
import workflow_tool as workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="matric-workflow-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.value, self.files = deck_tool.load_deck(deck_tool.SKILL / "assets/starter")
        self.before = self.stage("before")

    def stage(self, name, value=None, resources=None):
        path = self.root / name
        path.mkdir()
        for filename, data in (resources or self.files).items():
            if filename != "deck2.json":
                (path / filename).write_bytes(data)
        (path / "deck2.json").write_text(json.dumps(value or self.value), encoding="utf-8")
        return path

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def profile(self):
        path = self.root / "X-Plane Keys.prf"
        path.write_text("I\n1005 version\nG CTRL sim/synthetic/gear\n", encoding="utf-8")
        return path

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / "workflow_tool.py"), *map(str, args)],
                              capture_output=True, text=True, cwd=self.root)

    def first_control(self, value):
        return value["Pages"][0]["Controls"][0]

    def test_desktop_setup_separates_runtime_checks_from_user_confirmation(self):
        with patch.object(workflow.sys, "version_info", (3, 13)):
            report = workflow.setup_check(confirmations=["matric"])
        checks = {c["id"]: c for c in report["checks"]}
        self.assertFalse(report["blocked"])
        self.assertEqual(checks["python"]["status"], "checked")
        self.assertEqual(checks["skill_payload"]["status"], "checked")
        self.assertEqual(checks["matric"]["status"], "user_confirmed")
        report = workflow.setup_check()
        self.assertEqual(report["checks"][-1]["status"], "needs_confirmation")

    def test_old_python_is_reported_as_blocker(self):
        with patch.object(workflow.sys, "version_info", (3, 9)):
            report = workflow.setup_check()
        self.assertTrue(report["blocked"])

    def test_game_profiles_preserve_provenance_without_claiming_live_support(self):
        profile = self.profile()
        original = profile.read_bytes()
        report = workflow.setup_check("game", "xplane", [profile], required=["sim/synthetic/gear"])
        self.assertEqual(report["discovery"]["game"]["candidate_count"], 1)
        self.assertEqual(report["sources"][0]["sha256"], workflow.digest(original))
        self.assertEqual(next(c["status"] for c in report["checks"] if c["id"] == "active_profiles"), "needs_confirmation")
        self.assertEqual(profile.read_bytes(), original)
        report = workflow.setup_check("game", "xplane", [profile], active_confirmed=True)
        self.assertEqual(next(c["status"] for c in report["checks"] if c["id"] == "active_profiles"), "user_confirmed")

    def test_discovery_does_not_select_profiles(self):
        self.profile()
        report = workflow.setup_check("game", "xplane", discover_root=self.root)
        self.assertTrue(report["discovery"]["candidates"]["candidates"])
        self.assertFalse(report["sources"])
        self.assertEqual(next(c["status"] for c in report["checks"] if c["id"] == "profiles"), "needs_confirmation")

    def test_missing_required_action_and_malformed_profiles_are_blocked(self):
        report = workflow.setup_check("game", "xplane", [self.profile()], required=["sim/synthetic/missing"])
        self.assertTrue(report["blocked"])
        malformed = self.root / "bad.binds"
        malformed.write_text("<Root", encoding="utf-8")
        report = workflow.setup_check("game", "elite", [malformed])
        self.assertTrue(report["blocked"])

    def test_setup_rejects_misrouted_options(self):
        for options in ({"game": "xplane"}, {"obs_collection": "collection.json"}, {"dcs_definitions": "defs"}):
            with self.assertRaises(ValueError):
                workflow.setup_check(**options)

    def test_saved_obs_discovery_omits_unrelated_settings_and_keeps_integration_unconfirmed(self):
        path = self.write_json("obs.json", {"name": "Synthetic", "sources": [
            {"name": "Scene A", "id": "scene", "settings": {"items": []}},
            {"name": "Mic", "id": "wasapi_input_capture", "settings": {"password": "synthetic-secret"}}]})
        report = workflow.setup_check("obs", obs_collection=path)
        self.assertEqual(report["discovery"]["obs"][0]["scenes"], ["Scene A"])
        self.assertNotIn("synthetic-secret", json.dumps(report))
        self.assertEqual(next(c["status"] for c in report["checks"] if c["id"] == "obs"), "needs_confirmation")

    def test_obs_snapshot_is_historical_and_invalid_input_blocks(self):
        path = self.write_json("snapshot.json", {"origin": "obs_websocket", "live": True,
            "collections": [{"collection": "Synthetic", "containers": [], "sources": []}], "warnings": []})
        report = workflow.setup_check("obs", obs_snapshot=path)
        self.assertEqual(next(c["status"] for c in report["checks"] if c["id"] == "obs_configuration"), "checked")
        path.write_text('{"origin":"other"}', encoding="utf-8")
        self.assertTrue(workflow.setup_check("obs", obs_snapshot=path)["blocked"])

    def test_live_obs_uses_existing_read_only_helper_and_does_not_report_credentials(self):
        snapshot = {"origin": "obs_websocket", "live": True, "complete": True,
                    "collections": [{"collection": "Synthetic", "sources": [], "containers": []}], "warnings": []}
        with patch.dict(workflow.os.environ, {"SYNTHETIC_OBS_PASSWORD": "synthetic-secret"}):
            with patch("obs_live.discover", return_value=snapshot) as discover:
                report = workflow.setup_check("obs", obs_url="ws://127.0.0.1:4455", obs_password_env="SYNTHETIC_OBS_PASSWORD")
        discover.assert_called_once_with("ws://127.0.0.1:4455", "synthetic-secret", timeout=5, snapshot_timeout=30)
        self.assertNotIn("synthetic-secret", json.dumps(report))
        self.assertEqual(next(c["status"] for c in report["checks"] if c["id"] == "obs"), "needs_confirmation")
        with patch("obs_live.discover", side_effect=ValueError("synthetic-secret")):
            report = workflow.setup_check("obs", obs_url="ws://127.0.0.1:4455")
        self.assertTrue(report["blocked"])
        self.assertNotIn("synthetic-secret", json.dumps(report))

    def test_dcs_setup_uses_selected_definitions_and_never_confirms_installation(self):
        report = workflow.setup_check("dcs", dcs_definitions=deck_tool.SKILL / "assets/dcs-demo/SKILL_DEMO.json")
        self.assertEqual(report["discovery"]["dcs"]["aircraft"], "SKILL_DEMO")
        self.assertTrue(report["sources"])
        for identity in ("dcs", "dcs_bios", "dbmm"):
            self.assertEqual(next(c["status"] for c in report["checks"] if c["id"] == identity), "needs_confirmation")

    def test_handover_explains_actions_and_leaves_review_checks_unrecorded(self):
        report = workflow.handover(self.before)
        self.assertIn("LCONTROL+C", report["controls"][0]["purpose"])
        self.assertEqual(report["checks"]["structure"]["status"], "passed")
        for name in workflow.REVIEW_CHECKS:
            self.assertEqual(report["checks"][name]["status"], "not_recorded")
        self.assertEqual(report["controls"][0]["feedback"]["status"], "none_declared")
        self.assertTrue(report["controls"][0]["dependencies"])

    def test_handover_accepts_catalog_nullable_modifiers(self):
        value = copy.deepcopy(self.value)
        self.first_control(value)["ControlEvents"][0]["Actions"][0]["Modifiers"] = None
        report = workflow.handover(self.stage("no-modifiers", value))
        self.assertEqual(report["controls"][0]["purpose"], "Keyboard shortcut: C")

    def test_handover_never_copies_text_bodies_or_http_credentials(self):
        value = copy.deepcopy(self.value)
        control = self.first_control(value)
        control["ControlEvents"][0]["Actions"] = [deck_tool.action("ActionExecHttp", Url="https://synthetic.invalid/?token=synthetic-secret", Headers={"Authorization": "synthetic-secret"}, Body="synthetic-secret")]
        value["Pages"][1]["Controls"][0]["ControlEvents"][0]["Actions"][0]["TextValue"] = "synthetic-secret"
        report = workflow.handover(self.stage("http", value))
        self.assertNotIn("synthetic-secret", json.dumps(report))
        self.assertTrue(any(d["id"] == "http" for d in report["dependencies"]))

    def test_exact_payload_evidence_and_control_notes_are_recorded_separately(self):
        report = workflow.handover(self.before)
        evidence = self.write_json("evidence.json", {"schema_version": 1,
            "payload_sha256": report["deck"]["payload_sha256"],
            "checks": {"visual_review": {"status": "passed", "notes": "Synthetic offline comparison only."}},
            "controls": {report["controls"][0]["id"]: {"purpose": "Copy selection", "input_source": "Reviewed synthetic shortcut", "unresolved": ["Confirm application focus"]}}})
        report = workflow.handover(self.before, evidence_path=evidence)
        self.assertEqual(report["checks"]["visual_review"]["origin"], "recorded_evidence")
        self.assertEqual(report["checks"]["live_application"]["status"], "not_recorded")
        self.assertEqual(report["controls"][0]["unresolved"], ["Confirm application focus"])
        (self.before / "panel.svg").write_bytes(b"<svg>changed</svg>")
        with self.assertRaises(ValueError):
            workflow.handover(self.before, evidence_path=evidence)

    def test_evidence_cannot_claim_pass_without_notes_or_unknown_control(self):
        report = workflow.handover(self.before)
        for extra in ({"checks": {"native_import": {"status": "passed", "notes": ""}}},
                      {"controls": {"unknown-id": {"purpose": "Test"}}}):
            path = self.write_json("bad-evidence.json", dict(schema_version=1, payload_sha256=report["deck"]["payload_sha256"], **extra))
            with self.assertRaises(ValueError):
                workflow.handover(self.before, evidence_path=path)

    def test_recorded_failure_is_a_blocker_and_report_is_still_written(self):
        report = workflow.handover(self.before)
        evidence = self.write_json("failed.json", {"schema_version": 1, "payload_sha256": report["deck"]["payload_sha256"],
            "checks": {"visual_review": {"status": "failed", "notes": "Synthetic clipped label."}}})
        output = self.root / "handover.json"
        result = self.cli("handover", self.before, "--evidence", evidence, "--format", "json", "--output", output)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(output.read_text())["checks"]["visual_review"]["status"], "failed")

    def test_setup_and_profile_provenance_can_be_combined_and_rechecked(self):
        profile = self.profile()
        setup = workflow.setup_check("game", "xplane", [profile])
        path = self.write_json("setup.json", setup)
        report = workflow.handover(self.before, setup_path=path, profiles=[profile])
        self.assertEqual(len(report["sources"]), 1)
        self.assertEqual(report["source_checks"][0]["status"], "unchanged")
        profile.write_text("changed", encoding="utf-8")
        report = workflow.handover(self.before, setup_path=path)
        self.assertEqual(report["source_checks"][0]["status"], "changed")
        with self.assertRaises(ValueError):
            workflow.handover(self.before, setup_path=path, profiles=[profile])

    def test_dcs_handover_collects_required_outputs_without_live_test_claim(self):
        source = self.root / "dcs"
        dcs_bios.example(source)
        report = workflow.handover(source, dcs_definitions=deck_tool.SKILL / "assets/dcs-demo/SKILL_DEMO.json")
        self.assertFalse(report["dcs_audit"]["errors"])
        self.assertTrue(report["dcs_audit"]["required_outputs_by_module"])
        self.assertEqual(report["checks"]["live_application"]["status"], "not_recorded")
        self.assertTrue(any(c["feedback"]["variables"] for c in report["controls"]))

    def test_stage_and_archive_have_the_same_payload_fingerprint(self):
        archive = self.root / "synthetic.deck"
        with zipfile.ZipFile(archive, "w") as zipped:
            for path in self.before.iterdir():
                zipped.writestr(self.value["Id"] + "/" + path.name, path.read_bytes())
        self.assertEqual(workflow.handover(self.before)["deck"], workflow.handover(archive)["deck"])
        self.assertFalse(workflow.compare(self.before, archive)["changes"])

    def test_presentation_edits_are_separate_from_behavior(self):
        value = copy.deepcopy(self.value)
        control = self.first_control(value)
        control.update(Text="Copy selection", Width=1)
        control["Config"]["BackgroundColor"] = "#123456"
        result = workflow.compare(self.before, self.stage("after", value))
        self.assertTrue(result["presentation_only"])
        self.assertEqual(set(result["categories"]), {"appearance", "layout"})
        self.assertFalse(result["requires_behavior_review"])

    def test_shortcuts_feedback_name_toggle_and_unknown_fields_require_review(self):
        for index, change in enumerate((
            lambda c: c["ControlEvents"][0]["Actions"][0].update(KeyCode=86),
            lambda c: c["Config"].update(ControlBindings=[{"PropertyPath": "state.pressed", "VariableName": "synthetic", "Transform": "return value;"}]),
            lambda c: c.update(Name="http-result-identity"),
            lambda c: c["Config"].update(Toggle=True),
            lambda c: c.update(FutureMetadata={"opaque": True}),
        )):
            value = copy.deepcopy(self.value)
            change(self.first_control(value))
            result = workflow.compare(self.before, self.stage("edit" + str(index), value))
            self.assertTrue(result["requires_behavior_review"], result)
            self.assertFalse(result["presentation_only"])

    def test_modified_resources_are_included_even_when_json_is_unchanged(self):
        after = self.stage("resource")
        (after / "panel.svg").write_bytes(b"<svg>changed</svg>")
        result = workflow.compare(self.before, after)
        self.assertEqual(result["resources"][0]["name"], "panel.svg")
        self.assertTrue(result["requires_behavior_review"])
        self.assertFalse(result["changes"])

    def test_known_static_raster_artwork_is_presentation(self):
        value = copy.deepcopy(self.value)
        value["Pages"][0]["BackgroundImage"] = "panel.png"
        files = dict(self.files, **{"panel.png": b"synthetic-image-one"})
        before = self.stage("raster-before", value, files)
        files["panel.png"] = b"synthetic-image-two"
        after = self.stage("raster-after", value, files)
        self.assertTrue(workflow.compare(before, after)["presentation_only"])

    def test_dynamic_resource_and_center_button_changes_require_review(self):
        value = copy.deepcopy(self.value)
        self.first_control(value)["Config"]["AdditionalResources"] = {"test": "panel.svg"}
        result = workflow.compare(self.before, self.stage("dynamic", value))
        self.assertIn("dependencies", result["categories"])
        self.assertEqual(workflow.category(("Config", "ButtonSize"), "control"), "behavior")

    def test_control_order_removal_and_deck_identity_changes_are_not_presentation_only(self):
        for index, mutation in enumerate((
            lambda v: v["Pages"][0]["Controls"].reverse(),
            lambda v: v["Pages"][0]["Controls"].pop(),
            lambda v: v.update(Id="fresh-deck-identity"),
        )):
            value = copy.deepcopy(self.value)
            mutation(value)
            result = workflow.compare(self.before, self.stage("struct" + str(index), value))
            self.assertTrue(result["requires_behavior_review"])
            self.assertFalse(result["presentation_only"])

    def test_json_formatting_is_not_a_semantic_change(self):
        after = self.stage("formatted")
        (after / "deck2.json").write_text(json.dumps(self.value, indent=4, sort_keys=True), encoding="utf-8")
        result = workflow.compare(self.before, after)
        self.assertFalse(result["changes"])
        self.assertFalse(result["requires_behavior_review"])

    def test_profile_changes_and_missing_files_are_detected_from_baseline(self):
        profile = self.profile()
        baseline = self.write_json("baseline.json", workflow.handover(self.before, profiles=[profile]))
        self.assertEqual(workflow.compare(self.before, self.before, baseline)["source_checks"][0]["status"], "unchanged")
        profile.write_text("changed", encoding="utf-8")
        report = workflow.compare(self.before, self.before, baseline)
        self.assertTrue(report["input_sources_need_review"])
        self.assertEqual(report["source_checks"][0]["status"], "changed")
        result = self.cli("compare", self.before, self.before, "--baseline-report", baseline, "--presentation-only")
        self.assertEqual(result.returncode, 1, result.stderr)
        profile.unlink()
        self.assertEqual(workflow.compare(self.before, self.before, baseline)["source_checks"][0]["status"], "unavailable")

    def test_wrong_baseline_cannot_supply_provenance(self):
        baseline = workflow.handover(self.before)
        baseline["deck"]["payload_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            workflow.compare(self.before, self.before, self.write_json("wrong.json", baseline))

    def test_source_directory_fingerprint_detects_new_applet_files(self):
        path = self.root / "applet"
        path.mkdir()
        (path / "applet.html").write_text("<html>synthetic</html>", encoding="utf-8")
        recorded = workflow.fingerprint(path)
        (path / "new.js").write_text("/* synthetic */", encoding="utf-8")
        self.assertEqual(workflow.check_sources([recorded])[0]["status"], "changed")

    def test_applet_payload_changes_invalidate_evidence_and_are_detected_from_baseline(self):
        import applet_tool
        applet = self.root / "synthetic-applet"
        applet_tool.new(applet, "synthetic-widget", "Synthetic widget")
        value = copy.deepcopy(self.value)
        custom = deck_tool.new_control("MCCustom", "Synthetic", 0, 0, 2, 2)
        custom["Config"]["AppletId"] = "synthetic-widget"
        value["Pages"][0]["Controls"][0] = custom
        source = self.stage("with-applet", value)
        report = workflow.handover(source, [applet])
        baseline = self.write_json("applet-baseline.json", report)
        evidence = self.write_json("applet-evidence.json", {"schema_version": 1,
            "payload_sha256": report["deck"]["payload_sha256"], "applet_sha256": report["applet_sha256"],
            "checks": {"visual_review": {"status": "passed", "notes": "Synthetic applet render."}}})
        self.assertEqual(workflow.handover(source, [applet], evidence_path=evidence)["checks"]["visual_review"]["status"], "passed")
        with (applet / "main.js").open("a", encoding="utf-8") as output:
            output.write("\n/* synthetic revision */\n")
        with self.assertRaises(ValueError):
            workflow.handover(source, [applet], evidence_path=evidence)
        self.assertTrue(workflow.compare(source, source, baseline)["input_sources_need_review"])

    def test_reports_escape_labels_and_do_not_execute_them(self):
        value = copy.deepcopy(self.value)
        self.first_control(value)["Text"] = "[link](https://synthetic.invalid)\n<script>test</script>"
        text = workflow.markdown(workflow.handover(self.stage("labels", value)))
        self.assertNotIn("<script>", text)
        self.assertNotIn("[link](https://synthetic.invalid)", text)

    def test_cli_wont_overwrite_or_put_a_report_inside_a_staged_deck(self):
        nested = self.cli("handover", self.before, "--output", self.before / "notes.md")
        self.assertNotEqual(nested.returncode, 0)
        self.assertFalse((self.before / "notes.md").exists())
        output = self.root / "notes.md"
        first = self.cli("handover", self.before, "--output", output)
        self.assertEqual(first.returncode, 0, first.stderr)
        original = output.read_bytes()
        second = self.cli("handover", self.before, "--output", output)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(output.read_bytes(), original)

    def test_compare_guard_exits_nonzero_for_action_change_and_writes_report(self):
        value = copy.deepcopy(self.value)
        self.first_control(value)["ControlEvents"][0]["Actions"][0]["KeyCode"] = 86
        after = self.stage("shortcut", value)
        result = self.cli("compare", self.before, after, "--presentation-only", "--format", "json")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(json.loads(result.stdout)["requires_behavior_review"])


if __name__ == "__main__":
    unittest.main()
