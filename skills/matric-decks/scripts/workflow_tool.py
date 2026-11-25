#!/usr/bin/env python3
"""Check authoring setup, write deck handovers and compare revisions without executing actions."""
import argparse
import hashlib
import json
import os
import platform
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import deck_tool as deck
import game_bindings

SCHEMA_VERSION = 1
CONFIRMATIONS = ("matric", "obs", "dcs", "dcs_bios", "dbmm", "vjoy")
REVIEW_CHECKS = ("visual_review", "native_import", "physical_device", "live_application")
LAYOUT_FIELDS = {"X", "Y", "Width", "Height"}
# Only known presentation fields may be called appearance-only. New/opaque fields need review.
APPEARANCE_FIELDS = {
    "BackgroundColor", "BackgroundColorActive", "BackgroundImage", "BackgroundImageActive",
    "BackgroundSize", "TextColor", "TextColorActive", "FontFace", "TextSize", "Padding",
    "Halign", "Valign", "LabelCustomCSS", "LabelCustomCSSActive", "ButtonImage",
    "ButtonImageActive", "DialImage", "DialImageActive", "DialSize",
    "MaskImage", "MaskImageActive", "SwitchStateImages", "TrackBackgroundImage",
    "TrackFilledImage", "ThumbImage", "ThumbImageActive", "ThumbHeight", "ThumbWidth",
    "TrackColorBackground", "TrackColorFilled", "TrackSize", "TrackLength", "TrackThickness",
    "TrackOffsetX", "TrackOffsetY", "ShowValue",
}


def digest(data):
    """Return a SHA-256 fingerprint without retaining source contents in a report."""
    return hashlib.sha256(data).hexdigest()


def fingerprint(path):
    """Record an explicitly selected local input so a later revision can detect changes."""
    path = Path(path).resolve()
    if path.is_dir():
        files = {}
        for child in sorted(path.rglob("*")):
            if child.is_symlink():
                raise ValueError("Linked source directory contents are unsupported")
            if child.is_file():
                files[child.relative_to(path).as_posix()] = child.read_bytes()
        return {"path": str(path), "sha256": payload_sha256(files), "kind": "directory"}
    data = path.read_bytes()
    return {"path": str(path), "sha256": digest(data), "size": len(data)}


def payload_sha256(files):
    """Bind review evidence to every named payload file, independent of ZIP metadata."""
    entries = {name: digest(data) for name, data in sorted(files.items())}
    return digest(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def read_object(path):
    """Read strict JSON objects rather than evaluating configuration or scripts."""
    value = deck.read_json(Path(path).read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def report_base(kind):
    return {"schema_version": SCHEMA_VERSION, "kind": kind,
            "scope": "Checks files and setup information. Importing the deck or trying its controls is a separate step."}


def setup_check(target="desktop", game=None, profiles=(), discover_root=None, devices=None,
                active_confirmed=False, required=(), obs_collection=None, obs_snapshot=None,
                dcs_definitions=None, aircraft=None, confirmations=(), obs_url=None,
                obs_password_env=None):
    """Aggregate explicit local discovery inputs and keep user confirmations distinct from checks."""
    if target not in ("desktop", "obs", "dcs", "game"):
        raise ValueError("Unknown setup target")
    if set(confirmations) - set(CONFIRMATIONS):
        raise ValueError("Unknown prerequisite confirmation")
    if (game or profiles or discover_root or devices or active_confirmed or required) and target != "game":
        raise ValueError("Game profile options require --target game")
    if (obs_collection or obs_snapshot or obs_url or obs_password_env) and target != "obs":
        raise ValueError("OBS inputs require --target obs")
    if (dcs_definitions or aircraft) and target != "dcs":
        raise ValueError("DCS inputs require --target dcs")
    if target == "game" and game not in game_bindings.GAMES:
        raise ValueError("Choose a supported --game for game setup")
    if sum(bool(v) for v in (obs_collection, obs_snapshot, obs_url)) > 1:
        raise ValueError("Select one OBS collection, snapshot or live endpoint")
    if obs_password_env and (not obs_url or obs_password_env not in os.environ):
        raise ValueError("--obs-password-env requires a live endpoint and an existing environment variable")
    result = report_base("setup")
    result.update(target=target, checks=[], sources=[], discovery={}, warnings=[])

    def check(identity, status, detail):
        result["checks"].append({"id": identity, "status": status, "detail": detail})

    check("python", "checked" if sys.version_info >= (3, 11) else "blocked",
          "Python " + platform.python_version() + " is installed. The skill needs version 3.11 or newer.")
    try:
        # Exercise the portable payload rather than requiring a repository checkout or binaries.
        starter, files = deck.load_deck(deck.SKILL / "assets/starter")
        validation = deck.validate(starter, files)
        if validation["errors"]:
            raise ValueError("Bundled starter failed structural validation")
        required_files = ("SKILL.md", "LICENSE.txt", "scripts/applet_tool.py", "scripts/obs_live.py",
                          "scripts/dcs_bios.py", "scripts/driving_bindings.py", "scripts/ksp_bindings.py")
        if any(not (deck.SKILL / name).is_file() for name in required_files):
            raise ValueError("Portable skill files are missing")
        check("skill_payload", "checked", "The skill's tools, control definitions and starter deck are available.")
    except (OSError, ValueError, KeyError, TypeError) as error:
        check("skill_payload", "blocked", str(error))

    prerequisites = ["matric"]
    if target == "obs":
        prerequisites.append("obs")
        if obs_collection or obs_snapshot or obs_url:
            try:
                source = obs_collection or obs_snapshot
                if obs_collection:
                    import obs_inventory
                    inventory = obs_inventory.inventory(source)
                    collections = [inventory]
                    warnings = inventory["warnings"]
                    description = "Your saved OBS collection is readable. The connection between MATRIC and OBS still needs checking."
                else:
                    if obs_url:
                        import obs_live
                        snapshot = obs_live.discover(obs_url, os.environ.get(obs_password_env or "OBS_WEBSOCKET_PASSWORD"),
                                                     timeout=5, snapshot_timeout=30)
                    else:
                        snapshot = read_object(source)
                    collections = snapshot.get("collections")
                    if (snapshot.get("origin") != "obs_websocket" or snapshot.get("live") is not True
                            or not isinstance(collections, list) or not collections
                            or not all(isinstance(c, dict) and isinstance(c.get("sources"), list)
                                       and isinstance(c.get("containers"), list) for c in collections)):
                        raise ValueError("Expected an obs_live.py snapshot")
                    warnings = snapshot.get("warnings", [])
                    description = ("Read the scenes and sources from OBS. The connection through MATRIC still needs checking."
                                   if obs_url else "Your saved OBS snapshot is readable. Scenes and states may have changed since it was captured.")
                    result["discovery"]["obs_snapshot"] = {key: snapshot.get(key) for key in ("started_at", "completed_at", "complete", "scope")}
                if source:
                    result["sources"].append(fingerprint(source))
                result["discovery"]["obs"] = [
                    {"collection": c.get("collection"), "scenes": [s.get("name") for s in c["containers"] if s.get("kind") == "scene"],
                     "source_count": len(c["sources"])} for c in collections]
                if not isinstance(warnings, list) or not all(isinstance(w, str) for w in warnings):
                    raise ValueError("Invalid snapshot warnings")
                result["warnings"].extend(warnings)
                check("obs_configuration", "checked", description)
            except (OSError, ValueError, KeyError, TypeError):
                check("obs_configuration", "blocked", "Couldn't read the OBS settings. Check the file or your OBS WebSocket connection settings.")
        else:
            check("obs_configuration", "needs_confirmation", "Choose an exported OBS collection, a saved snapshot or an OBS WebSocket connection to inspect.")
    elif target == "game":
        if discover_root:
            try:
                result["discovery"]["candidates"] = game_bindings.discover(game, discover_root)
                check("profile_discovery", "checked", "Listed the profiles in your chosen folder. Choose the ones you use in the game.")
            except (OSError, ValueError, KeyError, TypeError, ET.ParseError):
                check("profile_discovery", "blocked", "Couldn't look for profiles in the chosen folder. Check its location.")
        if profiles:
            try:
                mapping = read_object(devices) if devices else {}
                inventory = game_bindings.inventory(game, profiles, mapping, required, active_confirmed)
                result["sources"].extend(inventory["sources"])
                if devices:
                    result["sources"].append(fingerprint(devices))
                    prerequisites.append("vjoy")
                result["discovery"]["game"] = {
                    "game": game, "binding_count": len(inventory["bindings"]),
                    "candidate_count": sum(b["candidate"] is not None for b in inventory["bindings"]),
                    "conflicts": inventory["conflicts"], "missing_actions": inventory["missing_actions"]}
                result["warnings"].extend(inventory["warnings"])
                status = "blocked" if inventory["missing_actions"] else "checked"
                detail = ("These controls don't have bindings in the selected profiles: " + ", ".join(inventory["missing_actions"])
                          if inventory["missing_actions"] else "Read the saved bindings. Check when each input applies and whether it needs a tap or a hold.")
                check("profiles", status, detail)
                check("active_profiles", "user_confirmed" if active_confirmed else "needs_confirmation",
                      "You confirmed these are the profiles you're using." if active_confirmed else "Check that these are the profiles selected in the game, including any aircraft-specific settings.")
                if inventory["conflicts"]:
                    check("input_conflicts", "needs_confirmation", "Some controls share an input. Check which profiles and modes use them.")
                if not inventory["bindings"]:
                    check("usable_bindings", "needs_confirmation", "No supported bindings were found. Choose another profile or add bindings in the game.")
            except (OSError, ValueError, KeyError, TypeError, ET.ParseError):
                check("profiles", "blocked", "Couldn't read the chosen profiles or device mapping. Check the files with game_bindings.py inventory.")
        else:
            check("profiles", "needs_confirmation", "Choose the profile files you use. Finding a profile doesn't tell us whether it is selected in the game.")
    elif target == "dcs":
        prerequisites.extend(("dcs", "dcs_bios", "dbmm"))
        if dcs_definitions:
            try:
                import dcs_bios
                inventory = dcs_bios.load_definitions(dcs_definitions, aircraft)
                result["discovery"]["dcs"] = {key: inventory[key] for key in ("aircraft", "modules", "definitions")}
                root = Path(dcs_definitions)
                root = root if root.is_dir() else root.parent
                result["sources"].extend(fingerprint(root / (module + ".json")) for module in inventory["modules"])
                if (root / "AircraftAliases.json").is_file():
                    result["sources"].append(fingerprint(root / "AircraftAliases.json"))
                check("aircraft_definitions", "checked", "Read the selected aircraft's control definitions. DCS-BIOS setup and the controls still need checking in DCS.")
            except (OSError, ValueError, KeyError, TypeError):
                check("aircraft_definitions", "blocked", "Couldn't load the aircraft's controls. Check the aircraft name and definitions folder.")
        else:
            check("aircraft_definitions", "needs_confirmation", "Choose your installed DCS-BIOS definitions and the aircraft to use.")
    details = {
        "matric": "Check that MATRIC works with your device and supports the features this deck needs.",
        "obs": "Check the connection between MATRIC and OBS. Reading your OBS settings doesn't check this connection.",
        "dcs": "Check that DCS and the aircraft module are installed.",
        "dcs_bios": "Install DCS-BIOS and enable the outputs this deck uses.",
        "dbmm": "Connect DCS-BIOS to MATRIC through DBMM and enable the values this deck uses.",
        "vjoy": "Check the vJoy driver, its available controls and how the game maps them.",
    }
    confirmed = {
        "matric": "You confirmed that MATRIC is set up.",
        "obs": "You confirmed the connection between MATRIC and OBS.",
        "dcs": "You confirmed that DCS and the aircraft module are available.",
        "dcs_bios": "You confirmed the DCS-BIOS setup.",
        "dbmm": "You confirmed the DBMM connection and settings.",
        "vjoy": "You confirmed the vJoy setup and its mapping in the game.",
    }
    for identity in dict.fromkeys(prerequisites + list(confirmations)):
        status = "user_confirmed" if identity in confirmations else "needs_confirmation"
        check(identity, status, confirmed[identity] if identity in confirmations else details[identity])
    result["warnings"] = list(dict.fromkeys(result["warnings"]))
    result["blocked"] = any(c["status"] == "blocked" for c in result["checks"])
    return result


def controls(value):
    """Yield page/control pairs with stable IDs; comparisons never guess matches from labels."""
    for page in value["Pages"]:
        for control in page["Controls"]:
            yield page, control


def dependencies(control):
    """Describe declared external requirements without copying action values or credentials."""
    config = control["Config"]
    found = {}
    def add(identity, detail):
        found[identity] = {"id": identity, "detail": detail}
    for event in control["ControlEvents"]:
        for action in event["Actions"]:
            kind = action.get("ActionTypeName", "").rsplit(".", 1)[-1]
            if kind.startswith("ActionOBS"):
                add("obs", "Connect MATRIC to OBS and check the scene and source names.")
            if kind.lower().startswith("actionvjoy"):
                add("vjoy", "Set up vJoy and check which device and inputs the game uses.")
            if kind in ("ActionHotkey", "ActionMacro", "ActionText"):
                add("application_input", "Check the shortcuts and keyboard layout, and keep the intended app focused when using them.")
            if kind in ("ActionRunApp", "ActionFocusApp", "ActionMixerMute", "ActionMixerVolume", "ActionMixerVolumeSet", "ActionMixerVolumeStep"):
                add("local_target", "Check that the selected app or audio device is available on your PC.")
            if kind == "ActionExecHttp":
                add("http", "Check the service address, sign-in settings and HTTP support in your MATRIC build.")
            if kind == "ActionLoadDeck":
                add("external_deck", "Install the other deck that this control opens.")
            if kind == "ActionStreamDeckContainer":
                add("streamdeck", "Stream Deck support is experimental. Install the plugin and check its settings and files against the supported features.")
            if action.get("VariableName") == "DCS_INPUT_COMMAND":
                add("dcs", "Set up DCS-BIOS and DBMM, then check the commands and exported values in DCS.")
    if config.get("AppletId"):
        add("applet:" + str(config["AppletId"]), "Install the matching .mapl separately before importing the deck.")
    if config.get("FontFace") not in (None, "text", "icon"):
        add("custom_font", "Install the chosen font separately; the deck doesn't include it.")
    if config.get("AdditionalResources"):
        add("additional_resources", "Use a MATRIC server and client that support the extra files selected by this deck's calculations.")
    if control["ControlTypeName"].endswith((".MCIframe", ".MCDesktopMirror")):
        add("external_display", "Check that the selected webpage or screen capture is available and displays correctly.")
    return [found[key] for key in sorted(found)]


def evidence_for(path, payload_hash, ids, applet_hashes=None):
    """Accept explicit review records only for the exact payload and known control identities."""
    if path is None:
        return {"checks": {}, "controls": {}}
    evidence = read_object(path)
    if set(evidence) - {"schema_version", "payload_sha256", "applet_sha256", "checks", "controls"}:
        raise ValueError("Unknown evidence fields")
    if evidence.get("schema_version") != SCHEMA_VERSION or evidence.get("payload_sha256") != payload_hash:
        raise ValueError("Evidence must match this schema and the exact deck payload fingerprint")
    if evidence.get("applet_sha256", {}) != (applet_hashes or {}):
        raise ValueError("Evidence must match all explicitly supplied applet payload fingerprints")
    checks = evidence.get("checks", {})
    notes = evidence.get("controls", {})
    if not isinstance(checks, dict) or not isinstance(notes, dict) or set(checks) - set(REVIEW_CHECKS) or set(notes) - ids:
        raise ValueError("Evidence references unknown checks or control IDs")
    for check in checks.values():
        if (not isinstance(check, dict) or set(check) != {"status", "notes"}
                or check["status"] not in ("passed", "failed", "not_checked")
                or not isinstance(check["notes"], str) or not check["notes"].strip()):
            raise ValueError("Review evidence requires status and nonempty notes")
    for note in notes.values():
        if not isinstance(note, dict) or set(note) - {"purpose", "input_source", "setup", "unresolved"}:
            raise ValueError("Unknown control evidence fields")
        for key, value in note.items():
            if key in ("purpose", "input_source"):
                valid = isinstance(value, str) and bool(value.strip())
            else:
                valid = isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)
            if not valid:
                raise ValueError("Invalid control evidence text/list")
    return {"checks": checks, "controls": notes}


def action_summary(action, page_titles):
    """Explain common configured inputs while omitting text bodies, URLs, headers and opaque settings."""
    kind = action["ActionTypeName"].rsplit(".", 1)[-1]
    description = deck.CATALOG["actions"][action["ActionTypeName"]]["description"]
    if kind == "ActionHotkey":
        key = action.get("Keystroke") or "key code " + str(action.get("KeyCode"))
        return "Keyboard shortcut: " + "+".join((action.get("Modifiers") or []) + [key])
    if kind == "ActionGoToPage":
        return "Open page: " + str(page_titles.get(action.get("TargetPageId"), action.get("TargetPageId")))
    if kind.startswith("ActionOBS"):
        names = [str(action[k]) for k in ("Scene", "Source") if action.get(k)]
        return "OBS " + str(action.get("Command") or "volume") + (": " + ", ".join(names) if names else "")
    if kind.lower().startswith("actionvjoy"):
        fields = [key + "=" + str(action[key]) for key in ("DeviceId", "ButtonId", "Axis", "HorizontalAxis", "VerticalAxis", "POVId", "POVDirection") if key in action]
        return description + " (" + ", ".join(fields) + ")"
    if action.get("VariableName") == "DCS_INPUT_COMMAND":
        return "Send a DCS-BIOS command through DBMM" + (" (calculated; review separately)" if action.get("VariableCalculateValueFunction") else "")
    return description


def handover(source, applet_paths=(), setup_path=None, evidence_path=None, profiles=(),
             dcs_definitions=None, aircraft=None):
    """Combine package facts and explicit review evidence into a customer-readable handover."""
    if aircraft and not dcs_definitions:
        raise ValueError("--aircraft requires --dcs-definitions")
    value, files = deck.load_deck(source)
    from applet_tool import load_manifests, load as load_applet
    applets = load_manifests(applet_paths) if applet_paths else None
    validation = deck.validate(value, files, applets)
    if validation["errors"]:
        raise ValueError("Fix structural errors before producing a handover: " + "; ".join(validation["errors"]))
    result = report_base("handover")
    result.update(deck={"id": value["Id"], "title": value.get("Title", ""), "payload_sha256": payload_sha256(files)},
                  validation=validation, sources=[fingerprint(p) for p in profiles], controls=[], dependencies=[])
    result["applet_sha256"] = {}
    for path in applet_paths:
        manifest, applet_files = load_applet(path)
        result["applet_sha256"][manifest["AppletId"]] = payload_sha256(applet_files)
        result["sources"].append(fingerprint(path))
    evidence = evidence_for(evidence_path, result["deck"]["payload_sha256"],
                            {c["Id"] for _, c in controls(value)}, result["applet_sha256"])
    result["checks"] = {"structure": {"status": "passed", "origin": "tool", "notes": "The deck files passed the format and resource checks."}}
    for name in REVIEW_CHECKS:
        result["checks"][name] = dict(evidence["checks"].get(name, {"status": "not_recorded", "notes": "No check notes have been added yet."}),
                                     origin="recorded_evidence" if name in evidence["checks"] else "not_checked")
    if setup_path:
        setup = read_object(setup_path)
        if (setup.get("schema_version") != SCHEMA_VERSION or setup.get("kind") != "setup"
                or not isinstance(setup.get("checks"), list) or not isinstance(setup.get("sources"), list)
                or not all(isinstance(c, dict) and set(c) == {"id", "status", "detail"}
                           and all(isinstance(v, str) for v in c.values())
                           and c["status"] in ("checked", "blocked", "user_confirmed", "needs_confirmation")
                           for c in setup["checks"])
                or not isinstance(setup.get("warnings"), list)
                or not all(isinstance(w, str) for w in setup["warnings"])):
            raise ValueError("Expected a setup JSON report from this helper")
        # Whitelist fields; never copy raw discovery configuration into a handover.
        result["setup"] = {"target": setup.get("target"), "checks": setup["checks"], "warnings": setup.get("warnings", [])}
        result["sources"].extend(setup["sources"])
    all_dependencies = {"matric": {"id": "matric", "detail": "Import the deck into MATRIC and check that your server and client support its features."}}
    page_titles = {p["Id"]: p.get("Title") or p["Id"] for p in value["Pages"]}
    for page, control in controls(value):
        config = control["Config"]
        bindings = config.get("ControlBindings") or []
        variables = {b["VariableName"] for b in bindings if isinstance(b, dict) and isinstance(b.get("VariableName"), str)}
        manifest = (applets or {}).get(config.get("AppletId"))
        if manifest:
            parameters = config.get("AppletParams") or {}
            for parameter in manifest["AppletParams"]:
                if parameter["ParamType"] == "variable":
                    name = parameters.get(parameter["Name"], parameter.get("Default"))
                    if isinstance(name, str) and name:
                        variables.add(name)
        requirements = dependencies(control)
        if any(v.startswith("dcs_") for v in variables) and not any(d["id"] == "dcs" for d in requirements):
            requirements.append({"id": "dcs", "detail": "Enable the DCS-BIOS/DBMM values used by this control's display."})
        for requirement in requirements:
            all_dependencies[requirement["id"]] = requirement
        actions = [{"event": event["Name"], "actions": [action_summary(a, page_titles) for a in event["Actions"]]}
                   for event in control["ControlEvents"] if event["Actions"]]
        note = evidence["controls"].get(control["Id"], {})
        result["controls"].append({
            "id": control["Id"], "page": page.get("Title") or page["Id"],
            "label": control.get("Text") or control.get("Name") or control["Id"],
            "purpose": note.get("purpose", control.get("Description") or "; ".join(a for event in actions for a in event["actions"]) or "No actions added. Check whether this is a display or a control that still needs connecting."),
            "input_source": note.get("input_source", "Source not added yet. Check these bindings against your app settings."),
            "actions": actions, "dependencies": requirements, "setup": note.get("setup", []),
            "unresolved": note.get("unresolved", []),
            "feedback": {"status": "configured" if variables else ("unknown" if config.get("AppletId") else "none_declared"),
                         "variables": sorted(variables),
                         "detail": ("Feedback connections are listed. Check that they show the app's actual state." if variables else
                                    "Check this widget's feedback in MATRIC." if config.get("AppletId") else
                                    "No feedback connection is listed. Check the app itself for its current state.")}
        })
    result["dependencies"] = [all_dependencies[key] for key in sorted(all_dependencies)]
    if dcs_definitions:
        import dcs_bios
        catalog = dcs_bios.load_definitions(dcs_definitions, aircraft)
        result["dcs_audit"] = dcs_bios.audit(value, files, catalog, applets)
        root = Path(dcs_definitions)
        root = root if root.is_dir() else root.parent
        result["sources"].extend(fingerprint(root / (m + ".json")) for m in catalog["modules"])
        if (root / "AircraftAliases.json").is_file():
            result["sources"].append(fingerprint(root / "AircraftAliases.json"))
    sources = {}
    for item in result["sources"]:
        item = {key: item[key] for key in ("path", "sha256", "size", "kind", "modified_utc") if key in item}
        if item["path"] in sources and item["sha256"] != sources[item["path"]]["sha256"]:
            raise ValueError("A setup source changed since discovery; rerun setup before handover")
        sources[item["path"]] = item
    result["sources"] = [sources[key] for key in sorted(sources)]
    result["source_checks"] = check_sources(result["sources"])
    result["blocked"] = (any(c["status"] == "failed" for c in result["checks"].values())
                         or bool(result.get("dcs_audit", {}).get("errors"))
                         or any(c["status"] == "blocked" for c in result.get("setup", {}).get("checks", [])))
    return result


def check_sources(sources):
    """Re-read recorded explicit paths; report missing/changed files without exposing their contents."""
    result = []
    for item in sources:
        if (not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"]
                or not Path(item["path"]).is_absolute() or not isinstance(item.get("sha256"), str)
                or len(item["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in item["sha256"])):
            raise ValueError("Invalid recorded source fingerprint")
        try:
            current = fingerprint(item["path"])
            status = "unchanged" if item["sha256"] == current["sha256"] else "changed"
        except (OSError, ValueError):
            current, status = None, "unavailable"
        result.append({"path": item["path"], "status": status, "before_sha256": item["sha256"],
                       "current_sha256": current["sha256"] if current else None})
    return result


def changed_paths(before, after, prefix=()):
    """Compare typed JSON values without discarding list order or opaque configuration."""
    if type(before) is not type(after):
        return [prefix]
    if isinstance(before, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            result.extend(changed_paths(before[key], after[key], prefix + (key,))
                          if key in before and key in after else [prefix + (key,)])
        return result
    if isinstance(before, list):
        result = []
        for index in range(max(len(before), len(after))):
            result.extend(changed_paths(before[index], after[index], prefix + (str(index),))
                          if index < min(len(before), len(after)) else [prefix + (str(index),)])
        return result
    return [] if before == after else [prefix]


def pointer(path):
    return "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in path)


def category(path, scope):
    """Conservatively separate known presentation edits from behavior and unknown fields."""
    if not path:
        return "other"
    key = path[0]
    if scope == "control":
        if key in LAYOUT_FIELDS:
            return "layout"
        if key == "Text":
            return "appearance"
        if key == "Description":
            return "metadata"
        if key == "ControlEvents" or key in ("ControlTypeName", "ControlConfigTypeName", "Name"):
            return "behavior"
        if key == "Config" and len(path) > 1:
            if path[1] == "ControlBindings":
                return "feedback"
            if path[1] in ("AdditionalResources", "AppletId", "AppletParams", "AllowedFeatures"):
                return "dependencies"
            return "appearance" if path[1] in APPEARANCE_FIELDS else "behavior"
    elif scope == "page":
        if key in ("Cols", "Rows"):
            return "layout"
        if key == "Title":
            return "metadata"
        if key in APPEARANCE_FIELDS:
            return "appearance"
    elif scope == "deck":
        if key in ("Title", "Description", "Author"):
            return "metadata"
        if key in ("DefaultPageId", "ReferencedUserVariables"):
            return "behavior"
    return "other"


def asset_roles(value):
    """Recognize explicitly referenced native artwork; unknown/dynamic assets require review."""
    roles = {}
    def mark(name, role):
        if isinstance(name, str) and name:
            roles.setdefault(name, set()).add(role)
    def walk(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key.endswith(("Image", "ImageActive")):
                    mark(child, "appearance")
                elif key == "SwitchStateImages" and isinstance(child, list):
                    for name in child:
                        mark(name, "appearance")
                elif key == "AdditionalResources" and isinstance(child, dict):
                    for name in child.values():
                        mark(name, "dependencies")
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
    walk(value)
    return roles


def compare(before_source, after_source, baseline_report=None):
    """Compare stable deck identities and all serialized data, plus optional saved input fingerprints."""
    before, before_files = deck.load_deck(before_source)
    after, after_files = deck.load_deck(after_source)
    for value, files in ((before, before_files), (after, after_files)):
        validation = deck.validate(value, files)
        if validation["errors"]:
            raise ValueError("Fix structural errors before comparison: " + "; ".join(validation["errors"]))
    result = report_base("comparison")
    result.update(before_payload_sha256=payload_sha256(before_files), after_payload_sha256=payload_sha256(after_files),
                  deck_identity_changed=before["Id"] != after["Id"], changes=[], resources=[], source_checks=[],
                  source_check_status="not_recorded")
    def fields(old, new, scope, identity):
        for path in changed_paths(old, new):
            result["changes"].append({"scope": scope, "id": identity, "path": pointer(path), "category": category(path, scope)})
    fields({k: v for k, v in before.items() if k != "Pages"},
           {k: v for k, v in after.items() if k != "Pages"}, "deck", after["Id"])
    old_pages, new_pages = ({p["Id"]: p for p in v["Pages"]} for v in (before, after))
    if [p["Id"] for p in before["Pages"]] != [p["Id"] for p in after["Pages"]]:
        result["changes"].append({"scope": "deck", "id": after["Id"], "path": "/Pages/order", "category": "structure"})
    for identity in sorted(old_pages.keys() | new_pages.keys()):
        if identity not in old_pages or identity not in new_pages:
            result["changes"].append({"scope": "page", "id": identity, "path": "/",
                                      "category": "structure", "change": "added" if identity in new_pages else "removed"})
        else:
            fields({k: v for k, v in old_pages[identity].items() if k != "Controls"},
                   {k: v for k, v in new_pages[identity].items() if k != "Controls"}, "page", identity)
            if [c["Id"] for c in old_pages[identity]["Controls"]] != [c["Id"] for c in new_pages[identity]["Controls"]]:
                result["changes"].append({"scope": "page", "id": identity, "path": "/Controls/order", "category": "structure"})
    old_controls, new_controls = ({c["Id"]: (p["Id"], c) for p, c in controls(v)} for v in (before, after))
    for identity in sorted(old_controls.keys() | new_controls.keys()):
        if identity not in old_controls or identity not in new_controls:
            result["changes"].append({"scope": "control", "id": identity, "path": "/", "category": "structure",
                                      "change": "added" if identity in new_controls else "removed"})
        else:
            if old_controls[identity][0] != new_controls[identity][0]:
                result["changes"].append({"scope": "control", "id": identity, "path": "/page", "category": "structure"})
            fields(old_controls[identity][1], new_controls[identity][1], "control", identity)
    roles_before, roles_after = asset_roles(before), asset_roles(after)
    for name in sorted(before_files.keys() | after_files.keys()):
        if name == "deck2.json" or before_files.get(name) == after_files.get(name):
            continue
        roles = roles_before.get(name, set()) | roles_after.get(name, set())
        # SVG can contain executable content/external references; changed SVG bytes need review too.
        presentation = roles == {"appearance"} and Path(name).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
        result["resources"].append({"name": name, "category": "appearance" if presentation else "dependencies",
                                    "change": "added" if name not in before_files else "removed" if name not in after_files else "changed",
                                    "before_sha256": digest(before_files[name]) if name in before_files else None,
                                    "after_sha256": digest(after_files[name]) if name in after_files else None})
    if baseline_report:
        baseline = read_object(baseline_report)
        if (baseline.get("schema_version") != SCHEMA_VERSION or baseline.get("kind") != "handover"
                or not isinstance(baseline.get("deck"), dict)
                or baseline.get("deck", {}).get("payload_sha256") != result["before_payload_sha256"]
                or not isinstance(baseline.get("sources"), list)):
            raise ValueError("Baseline must be a handover JSON report for the exact before payload")
        result["source_checks"] = check_sources(baseline["sources"])
        result["source_check_status"] = "checked" if baseline["sources"] else "no_sources_recorded"
    categories = {c["category"] for c in result["changes"] + result["resources"]}
    result["categories"] = sorted(categories)
    result["requires_behavior_review"] = bool(categories - {"appearance", "layout", "metadata"})
    result["input_sources_need_review"] = any(s["status"] != "unchanged" for s in result["source_checks"])
    result["presentation_only"] = bool(categories) and not result["requires_behavior_review"] and not result["input_sources_need_review"]
    result["limits"] = "Saved settings and files were compared; the controls and scripts weren't run. Try the revised layout on your device. Use an earlier handover report to check setup-file changes too. Applet files are checked for changes, not how their code behaves."
    return result


def markdown(report):
    """Explain results in plain language and keep troubleshooting data in expandable details."""
    def text(value):
        # Escape HTML and Markdown so labels cannot turn into links, images or table rows.
        value = str(value).replace("\r", " ").replace("\n", " ")
        for char, replacement in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ("\\", "\\\\")):
            value = value.replace(char, replacement)
        for char in "`*_{}[]()|#!":
            value = value.replace(char, "\\" + char)
        return value
    names = {
        "python": "Python", "skill_payload": "Skill files", "obs_configuration": "OBS settings",
        "matric": "MATRIC", "obs": "OBS connection", "dcs": "DCS", "dcs_bios": "DCS-BIOS",
        "dbmm": "DBMM", "vjoy": "vJoy", "profile_discovery": "Find game profiles",
        "profiles": "Game bindings", "active_profiles": "Selected game profiles",
        "input_conflicts": "Shared inputs", "usable_bindings": "Available bindings",
        "aircraft_definitions": "Aircraft controls", "structure": "Deck files",
        "visual_review": "Layout and appearance", "native_import": "Import into MATRIC",
        "physical_device": "On your phone or tablet", "live_application": "With the app or game",
        "application_input": "App shortcuts", "local_target": "Apps and audio devices",
        "http": "Web service", "external_deck": "Linked deck", "streamdeck": "Stream Deck plugin",
        "custom_font": "Custom font", "additional_resources": "Extra control images and files",
        "external_display": "Webpage or screen capture",
    }
    def name(identity):
        if identity.startswith("applet:"):
            return "Widget " + identity[len("applet:"):]
        return names.get(identity, identity.replace("_", " ").capitalize())
    setup_status = {"checked": "Checked", "user_confirmed": "Confirmed by you",
                    "needs_confirmation": "Please confirm", "blocked": "Needs fixing"}
    technical = []
    lines = ["# MATRIC " + {"setup": "setup check", "handover": "deck guide", "comparison": "what changed"}[report["kind"]], ""]
    def bullets(items):
        items = list(items)
        if items:
            lines.append("")
            lines.extend("- " + text(item) for item in items)
    def setup_table(checks):
        lines.extend(["| Check | Status | What it means |", "| --- | --- | --- |"])
        for check in checks:
            values = (name(check["id"]), setup_status[check["status"]], check["detail"])
            lines.append("| " + " | ".join(text(v) for v in values) + " |")
    if report["kind"] == "setup":
        lines.extend(["Here's what was found and what still needs setting up.", ""])
        setup_table(report["checks"])
        discovery = report["discovery"]
        if discovery:
            lines.extend(["", "## What was found", ""])
            for collection in discovery.get("obs", []):
                lines.append("OBS collection: " + text(collection.get("collection") or "Unnamed"))
                bullets(["Scenes: " + ", ".join(str(s) for s in collection["scenes"]),
                         "Sources: " + str(collection["source_count"])])
            if "game" in discovery:
                game = discovery["game"]
                bullets(["Bindings found: " + str(game["binding_count"]),
                         "Inputs suggested for MATRIC: " + str(game["candidate_count"])])
                if game["missing_actions"]:
                    bullets(["Bindings still needed: " + ", ".join(game["missing_actions"])])
                if game["conflicts"]:
                    bullets([str(len(game["conflicts"])) + " groups of shared inputs need checking."])
            if "dcs" in discovery:
                lines.append("Aircraft: " + text(discovery["dcs"]["aircraft"]))
            if "candidates" in discovery:
                candidates = discovery["candidates"]["candidates"]
                bullets([str(len(candidates)) + " profile candidates found. Choose the profiles selected in your game."])
            technical.extend(["### Discovery details", "", "```json",
                              json.dumps(discovery, ensure_ascii=False, indent=2).replace("`", "\\u0060"), "```", ""])
        if report["warnings"]:
            lines.extend(["", "## Things to check"])
            bullets(report["warnings"])
    elif report["kind"] == "handover":
        lines.extend([text(report["deck"]["title"]), "", "Here's what your deck does and what to check next.", "",
                      "## What's been checked", "", "| Check | Result | Notes or next step |", "| --- | --- | --- |"])
        next_steps = {"visual_review": "Look over the layout and labels.",
                      "native_import": "Try importing the deck into MATRIC.",
                      "physical_device": "Check labels, spacing and touch controls on your device.",
                      "live_application": "Try the controls with the intended app or game."}
        review_status = {"passed": "Passed", "failed": "Needs fixing", "not_checked": "Not checked yet",
                         "not_recorded": "Not checked here yet"}
        for identity, check in report["checks"].items():
            status = review_status[check["status"]]
            if check["origin"] == "recorded_evidence":
                status += " (from review notes)"
            detail = next_steps[identity] if check["status"] == "not_recorded" else check["notes"]
            lines.append("| " + " | ".join(text(v) for v in (name(identity), status, detail)) + " |")
        technical.extend(["Deck ID: " + text(report["deck"]["id"]), "", "Deck file fingerprint: " + report["deck"]["payload_sha256"], ""])
        if report["applet_sha256"]:
            technical.extend(["Widget file fingerprints: " + text(json.dumps(report["applet_sha256"], sort_keys=True)), ""])
        lines.extend(["", "## Getting set up"])
        bullets(name(d["id"]) + ": " + d["detail"] for d in report["dependencies"])
        if "setup" in report:
            lines.extend(["", "### Your earlier setup check", ""])
            setup_table(report["setup"]["checks"])
            bullets(report["setup"]["warnings"])
        for control in report["controls"]:
            lines.extend(["", "## " + text(control["page"] + " / " + control["label"]), "",
                          text(control["purpose"]), "", "Based on: " + text(control["input_source"]), "",
                          "App feedback: " + text(control["feedback"]["detail"])])
            event_names = {"press": "On press", "release": "On release", "valuechange": "On adjustment",
                           "clockwise": "Turn clockwise", "counterclockwise": "Turn counterclockwise"}
            bullets(event_names.get(a["event"], a["event"]) + ": " + "; ".join(a["actions"]) for a in control["actions"])
            bullets("Setup: " + detail for detail in control["setup"])
            bullets("Still to do: " + detail for detail in control["unresolved"])
            technical.extend([text(control["label"]) + " — control ID: " + text(control["id"]), ""])
            if control["feedback"]["variables"]:
                technical.extend(["Feedback variables: " + text(", ".join(control["feedback"]["variables"])), ""])
        warnings = list(report["validation"]["warnings"])
        if "dcs_audit" in report:
            audit = report["dcs_audit"]
            warnings.extend("DCS needs fixing: " + w for w in audit["errors"])
            warnings.extend(audit["warnings"])
            technical.extend(["DCS outputs to enable: " + text(json.dumps(audit.get("required_outputs_by_module", {}), sort_keys=True)), ""])
        if warnings:
            lines.extend(["", "## Things to check"])
            bullets(dict.fromkeys(warnings))
    else:
        if report["requires_behavior_review"]:
            lines.append("This update changes more than appearance or layout. Check the changes before using the revised deck.")
        elif report["changes"] or report["resources"]:
            lines.append("Only appearance, layout or description details changed. The saved actions and feedback settings are unchanged.")
        else:
            lines.append("No changes to the deck's settings or resources.")
        if report["input_sources_need_review"]:
            lines.extend(["", "A setup file has changed or couldn't be read. Check the deck's bindings against your current settings."])
        if report["deck_identity_changed"]:
            lines.extend(["", "This revision uses a different deck ID. Treat it as a separate deck when importing."])
        changes = {"appearance": "Control appearance", "layout": "Control sizes or positions",
                   "metadata": "Names or descriptions", "behavior": "Control actions or behavior",
                   "feedback": "App feedback", "dependencies": "Connections, widgets or supporting files",
                   "structure": "Pages or control arrangement", "other": "Other settings that need checking"}
        if report["categories"]:
            lines.extend(["", "## What changed"])
            bullets(changes[c] for c in report["categories"])
        if report["resources"]:
            lines.extend(["", "## Changed files"])
            bullets(r["name"] + ": " + r["change"] for r in report["resources"])
        if report["source_check_status"] == "not_recorded":
            lines.extend(["", "Setup files weren't compared. Add the earlier handover report to check them too."])
        elif report["source_check_status"] == "no_sources_recorded":
            lines.extend(["", "The earlier handover didn't list any setup files to compare."])
        lines.extend(["", "These checks compare saved settings and files; they don't run the controls. Try the revised layout on your device."])
        technical.extend(["Before fingerprint: " + report["before_payload_sha256"], "", "After fingerprint: " + report["after_payload_sha256"], ""])
        technical.extend("- " + text(c["category"] + ": " + c["scope"] + " " + c["id"] + " " + c["path"] + " " + c.get("change", "changed")) for c in report["changes"])
    sources = report.get("source_checks", [])
    if sources:
        lines.extend(["", "## Your setup files"])
        source_status = {"unchanged": "Unchanged since the deck was prepared.",
                         "changed": "Changed. Check the deck's bindings against the updated file.",
                         "unavailable": "Couldn't read this file. It may have moved or been removed."}
        bullets(Path(s["path"]).name + ": " + source_status[s["status"]] for s in sources)
        technical.extend(["", "### Setup file details", ""])
        technical.extend("- " + text(s["path"] + ": " + s["status"]) for s in sources)
    elif report.get("sources"):
        lines.extend(["", "## Setup files saved for later checks"])
        bullets(Path(s["path"]).name for s in report["sources"])
        technical.extend(["### Setup file details", ""])
        technical.extend("- " + text(s["path"]) + ": " + s["sha256"] for s in report["sources"])
    if report["kind"] == "handover":
        lines.extend(["", "## Next steps", ""])
        if report["applet_sha256"] or any(d["id"].startswith("applet:") for d in report["dependencies"]):
            lines.append("Install the matching .mapl widgets first, then import the .deck into MATRIC.")
        else:
            lines.append("Import the .deck into MATRIC when you're ready to try it.")
        lines.extend(["", "Work through the items above, then try the controls with your app and on your device."])
    if technical:
        lines.extend(["", "<details>", "<summary>Technical details</summary>", "", *technical, "", "</details>"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup", help="Check portable authoring files and explicit local discovery inputs")
    setup.add_argument("--target", choices=("desktop", "obs", "dcs", "game"), default="desktop")
    setup.add_argument("--game", choices=game_bindings.GAMES)
    setup.add_argument("--profile", type=Path, action="append", default=[])
    setup.add_argument("--discover-root", type=Path)
    setup.add_argument("--device-map", type=Path)
    setup.add_argument("--active-confirmed", action="store_true")
    setup.add_argument("--require-action", action="append", default=[])
    obs = setup.add_mutually_exclusive_group()
    obs.add_argument("--obs-collection", type=Path)
    obs.add_argument("--obs-snapshot", type=Path)
    obs.add_argument("--obs-url", help="Explicit OBS WebSocket endpoint; only read-only discovery requests are sent")
    setup.add_argument("--obs-password-env", help="Password environment variable; defaults to OBS_WEBSOCKET_PASSWORD for live discovery")
    setup.add_argument("--confirm", choices=CONFIRMATIONS, action="append", default=[], help="Explicit user confirmation; never inferred from file discovery")
    delivery = commands.add_parser("handover", help="Describe a validated deck and separately recorded review evidence")
    delivery.add_argument("source", type=Path)
    delivery.add_argument("--applet", type=Path, action="append", default=[])
    delivery.add_argument("--setup-report", type=Path)
    delivery.add_argument("--evidence", type=Path)
    delivery.add_argument("--profile", type=Path, action="append", default=[])
    diff = commands.add_parser("compare", help="Compare deck revisions by stable identities and typed fields")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--baseline-report", type=Path)
    diff.add_argument("--presentation-only", action="store_true", help="Exit 1 if behavior/unknown/dependency or recorded source changes need review")
    for command in (setup, delivery):
        command.add_argument("--dcs-definitions", type=Path)
        command.add_argument("--aircraft")
    for command in (setup, delivery, diff):
        command.add_argument("--format", choices=("markdown", "json"), default="markdown")
        command.add_argument("--output", type=Path, help="New report outside all staged decks; existing files are never overwritten")
    args = parser.parse_args(argv)
    if args.output:
        if args.output.exists():
            parser.error("Output already exists; choose a new filename")
        inputs = [getattr(args, name, None) for name in ("source", "before", "after")]
        inputs += args.profile if hasattr(args, "profile") else []
        for source in filter(None, inputs):
            root = source.resolve() if source.is_dir() else source.resolve().parent if source.name == "deck2.json" else None
            if root is not None and (args.output.resolve() == root or root in args.output.resolve().parents):
                parser.error("Write reports outside staged deck directories")
    if args.command == "setup":
        result = setup_check(args.target, args.game, args.profile, args.discover_root, args.device_map,
                             args.active_confirmed, args.require_action, args.obs_collection, args.obs_snapshot,
                             args.dcs_definitions, args.aircraft, args.confirm, args.obs_url, args.obs_password_env)
        failed = result["blocked"]
    elif args.command == "handover":
        result = handover(args.source, args.applet, args.setup_report, args.evidence, args.profile,
                          args.dcs_definitions, args.aircraft)
        failed = result["blocked"]
    else:
        result = compare(args.before, args.after, args.baseline_report)
        failed = args.presentation_only and (result["requires_behavior_review"] or result["input_sources_need_review"])
    output = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n" if args.format == "json" else markdown(result)
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as report:
            report.write(output)
        print(args.output)
    else:
        print(output, end="")
    return int(failed)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        raise SystemExit(1)
