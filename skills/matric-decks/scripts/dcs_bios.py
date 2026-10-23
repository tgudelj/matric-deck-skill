#!/usr/bin/env python3
"""Inspect installed DCS-BIOS definitions and author/audit MATRIC DBMM bindings offline."""
import argparse
import copy
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path

import deck_tool as deck

MAILBOX = "DCS_INPUT_COMMAND"
IDENTIFIER = re.compile(r"[A-Za-z0-9_]+\Z")
VARIABLE_REF = re.compile(r"variables\s*\[\s*['\"](dcs_[A-Za-z0-9_]+)['\"]\s*\]")


def read(path):
    """Read JSON without evaluating Lua, JSONP or executable configuration."""
    return deck.read_json(Path(path).read_bytes())


def load_definitions(source, aircraft=None):
    """Resolve an exact module/aircraft alias against local JSON files, plus common metadata."""
    source = Path(source)
    root = source if source.is_dir() else source.parent
    available = {p.stem: p for p in root.glob("*.json") if p.name != "AircraftAliases.json"}
    alias_path = root / "AircraftAliases.json"
    aliases = read(alias_path) if alias_path.exists() else {}
    if not isinstance(aliases, dict):
        raise ValueError("AircraftAliases.json must map aircraft names to module-name arrays")
    if source.is_file():
        if source.name == "AircraftAliases.json":
            raise ValueError("Provide doc/json directory or a module JSON, not the aliases file")
        if aircraft and aircraft != source.stem and source.stem not in aliases.get(aircraft, []):
            raise ValueError("The supplied module JSON is not mapped to the requested aircraft")
        modules = [source.stem]
        aircraft = aircraft or source.stem
    else:
        if not aircraft:
            raise ValueError("Choose --aircraft from the installed aliases/modules, or provide one module JSON")
        modules = aliases.get(aircraft, [aircraft])
    if not isinstance(modules, list) or not modules or not all(isinstance(v, str) for v in modules):
        raise ValueError("The selected aircraft does not have a usable module list")
    requested = list(dict.fromkeys(modules))
    for module in requested:
        if module not in available:
            raise ValueError(f"Missing installed module JSON: {module}")
    modules = list(dict.fromkeys(requested + [m for m in ("CommonData", "MetadataStart", "MetadataEnd") if m in available]))
    controls, provenance = [], []
    for module in modules:
        path = available[module]
        raw = path.read_bytes()
        data = deck.read_json(raw)
        if not isinstance(data, dict):
            raise ValueError(f"{path.name}: expected category/control objects")
        provenance.append({"module": module, "sha256": hashlib.sha256(raw).hexdigest()})
        for category, entries in data.items():
            if not isinstance(entries, dict):
                raise ValueError(f"{path.name}: category {category!r} must contain controls")
            for key, item in entries.items():
                if not isinstance(item, dict):
                    raise ValueError(f"{path.name}: invalid control {key!r}")
                identifier = item.get("identifier", key)
                if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
                    raise ValueError(f"{path.name}: invalid identifier {identifier!r}")
                inputs, outputs = item.get("inputs", []), item.get("outputs", [])
                if not isinstance(inputs, list) or not isinstance(outputs, list) or not all(isinstance(v, dict) for v in inputs + outputs):
                    raise ValueError(f"{identifier}: inputs/outputs must be arrays of objects")
                controls.append({"module": module, "category": category, "identifier": identifier,
                                 "description": item.get("description", ""), "control_type": item.get("control_type"),
                                 "inputs": inputs, "outputs": outputs, "matric_variable": "dcs_" + identifier if outputs else None})
    return {"aircraft": aircraft, "modules": modules, "definitions": provenance, "controls": controls}


def find_control(catalog, identifier, module=None):
    """Reject missing or ambiguous identifiers instead of guessing among module definitions."""
    found = [c for c in catalog["controls"] if c["identifier"] == identifier and (module is None or c["module"] == module)]
    if len(found) != 1:
        raise ValueError(f"{identifier}: expected one definition, found {len(found)}; select the correct module")
    return found[0]


def command_text(control, argument):
    """Validate one literal DCS-BIOS argument using only this control's advertised interfaces."""
    if not isinstance(argument, (str, int)) or isinstance(argument, bool):
        raise ValueError("A command argument must be a string or integer")
    argument = str(argument)
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in argument):
        raise ValueError("One command only: arguments cannot contain control characters/newlines")
    valid = False
    for entry in control["inputs"]:
        interface = entry.get("interface")
        if interface == "action" and argument == str(entry.get("argument")):
            valid = True
        elif interface == "fixed_step" and argument in ("INC", "DEC"):
            valid = True
        elif interface == "set_state" and re.fullmatch(r"\d+", argument):
            maximum = entry.get("max_value")
            valid |= type(maximum) is int and 0 <= int(argument) <= maximum
        elif interface == "variable_step" and re.fullmatch(r"[+-]\d+", argument):
            maximum = entry.get("max_value")
            valid |= type(maximum) is int and 0 < abs(int(argument)) <= maximum
        elif interface == "set_string":
            valid = True  # Domain-specific frequency/text formatting still needs the control reference.
    if not valid:
        raise ValueError(f"{control['identifier']}: argument {argument!r} is not supported by its installed input interfaces")
    return control["identifier"] + " " + argument


def command_action(control, argument):
    """Create a native MATRIC action that writes one validated command to DBMM's mailbox."""
    return deck.action("ActionSetServerVariable", VariableName=MAILBOX, VariableType="STRING",
                       VariableValue=command_text(control, argument), VariableCalculateValueFunction=None)


def scaled_action(control):
    """Map MATRIC's 0..100 valuechange payload into a verified DCS-BIOS absolute set_state range."""
    entries = [i for i in control["inputs"] if i.get("interface") == "set_state"]
    if len(entries) != 1 or type(entries[0].get("max_value")) is not int or entries[0]["max_value"] <= 0:
        raise ValueError("Scaled input requires one set_state interface with a positive integer maximum")
    maximum = entries[0]["max_value"]
    prefix = json.dumps(control["identifier"] + " ")
    script = f"var percent = Number(eventData.value); if (!Number.isFinite(percent)) return ''; return {prefix} + Math.round(Math.max(0, Math.min(100, percent)) * {maximum} / 100);"
    return deck.action("ActionSetServerVariable", VariableName=MAILBOX, VariableType="STRING",
                       VariableValue="", VariableCalculateValueFunction=script)


def feedback(control, property_path, transform=""):
    """Build a binding only for a single unambiguous DBMM output; mapping semantics remain explicit."""
    if len(control["outputs"]) != 1 or control["outputs"][0].get("type") not in ("integer", "string"):
        raise ValueError("Choose a control with one supported output; DBMM does not distinguish output suffixes")
    return {"PropertyPath": property_path, "VariableName": control["matric_variable"], "Transform": transform}


def ensure_mailbox(value):
    """Initialize an empty persistent command variable; never copy a saved cockpit command into a new deck."""
    variables = value.setdefault("ReferencedUserVariables", [])
    if not isinstance(variables, list) or not all(isinstance(v, dict) for v in variables):
        raise ValueError("ReferencedUserVariables must contain variable objects")
    found = [v for v in variables if v.get("Name") == MAILBOX]
    if len(found) > 1:
        raise ValueError("Duplicate command mailbox declarations")
    config = {"Name": MAILBOX, "Value": "", "VariableType": "STRING", "CalculateValueFunction": None,
              "IsPersistent": True, "IsUserEditable": True}
    if found:
        found[0].update(config)
    else:
        variables.append(config)


def audit(value, files, catalog):
    """Check native structure, known commands and literal telemetry references without evaluating JavaScript."""
    report = deck.validate(value, files)
    if not isinstance(value, dict):
        return report
    references, commands, script_count = set(), [], 0
    def walk(item):
        nonlocal script_count
        if isinstance(item, dict):
            variable = item.get("VariableName")
            if isinstance(variable, str) and variable.startswith("dcs_"):
                references.add(variable)
            for key in ("Transform", "CalculateValueFunction", "VariableCalculateValueFunction"):
                script = item.get(key)
                if isinstance(script, str) and script:
                    references.update(VARIABLE_REF.findall(script))
                    script_count += 1
            if item.get("ActionTypeName") == deck.ACTION_PREFIX + "ActionSetServerVariable" and variable == MAILBOX:
                commands.append(item)
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
    walk(value)
    if script_count:
        report["warnings"].append("JavaScript is not evaluated; dynamically constructed variable names and command arguments need manual verification")
    for action in commands:
        if action.get("VariableType") != "STRING":
            report["errors"].append("DCS_INPUT_COMMAND actions must use VariableType STRING")
        script = action.get("VariableCalculateValueFunction")
        if script:
            if not isinstance(script, str):
                report["errors"].append("A calculated mailbox command must be JavaScript text")
                continue
            match = re.search(r"return\s+['\"]([A-Za-z0-9_]+) ['\"]", script)
            if match:
                try:
                    control = find_control(catalog, match[1])
                    if not control["inputs"]:
                        raise ValueError(f"{match[1]} has no command input")
                except ValueError as error:
                    report["errors"].append(str(error))
            else:
                report["warnings"].append("A calculated mailbox command has no recognized literal identifier; inspect it manually")
        else:
            command = action.get("VariableValue")
            try:
                if not isinstance(command, str) or " " not in command:
                    raise ValueError("Mailbox actions require an identifier and argument")
                identifier, argument = command.split(" ", 1)
                command_text(find_control(catalog, identifier), argument)
            except ValueError as error:
                report["errors"].append(str(error))
    declared = value.get("ReferencedUserVariables", [])
    if not isinstance(declared, list) or not all(isinstance(v, dict) for v in declared):
        report["errors"].append("ReferencedUserVariables must contain variable objects")
        declared = []
    if commands:
        mailbox = [v for v in declared if v.get("Name") == MAILBOX]
        if len(mailbox) != 1 or mailbox[0].get("Value") != "" or mailbox[0].get("VariableType") != "STRING" or mailbox[0].get("CalculateValueFunction"):
            report["errors"].append("Declare DCS_INPUT_COMMAND exactly once as an empty STRING with no calculation; never persist a pending command")
    required = {}
    for variable in sorted(references):
        try:
            control = find_control(catalog, variable[4:])
            if not control["outputs"]:
                raise ValueError(f"{variable} refers to an input-only control")
            if len(control["outputs"]) > 1:
                report["warnings"].append(f"{variable}: multiple outputs share one DBMM name; verify middleware behavior")
            required.setdefault(control["module"], []).append(control["identifier"])
        except ValueError as error:
            report["errors"].append(str(error))
    if any(v.get("CalculateValueFunction") and v.get("Name") != MAILBOX for v in declared):
        report["warnings"].append("Calculated user variables require explicit MATRIC setup; preserving ReferencedUserVariables does not register them in the inspected importer")
    if any(str(v.get("Name", "")).startswith("dcs_") for v in declared):
        report["warnings"].append("Deck declares dcs_ telemetry variables; normally DBMM owns these transient variables")
    report.update(aircraft=catalog["aircraft"], definitions=catalog["definitions"], command_actions=len(commands),
                  telemetry_variables=sorted(references), required_outputs_by_module=required)
    report["errors"] = list(dict.fromkeys(report["errors"]))
    report["warnings"] = list(dict.fromkeys(report["warnings"]))
    return report


def example(output):
    """Create a fresh synthetic training deck demonstrating momentary input, switch, slider and display feedback."""
    catalog = load_definitions(deck.SKILL / "assets/dcs-demo/SKILL_DEMO.json")
    button = deck.new_control("MCButton", "TEST", 0, 0, 2, 2)
    button["ControlEvents"] = [{"Name": name, "Actions": [command_action(find_control(catalog, "SYN_TEST_BUTTON"), val)]}
                               for name, val in (("press", 1), ("release", 0))]
    button["Config"]["ControlBindings"] = [feedback(find_control(catalog, "SYN_TEST_LAMP"), "state.pressed", "return Number(value) === 1;")]
    switch = deck.new_control("MCTwoPositionSwitch", "POWER", 2, 0, 2, 2)
    switch["ControlEvents"] = [{"Name": name, "Actions": [command_action(find_control(catalog, "SYN_POWER"), val)]}
                               for name, val in (("position-increment", 1), ("position-decrement", 0))]
    switch["Config"]["ControlBindings"] = [feedback(find_control(catalog, "SYN_POWER"), "state.position")]
    slider = deck.new_control("MCSlider", "DIMMER", 0, 2, 4, 1)
    slider["Config"]["SendValueAfterInteractionEnd"] = True
    slider["ControlEvents"] = [{"Name": "valuechange", "Actions": [scaled_action(find_control(catalog, "SYN_DIMMER"))]}]
    slider["Config"]["ControlBindings"] = [feedback(find_control(catalog, "SYN_DIMMER"), "state.value", "return Math.round(Number(value) * 100 / 65535);")]
    label = deck.new_control("MCButton", "SYNTHETIC DATA", 4, 0, 2, 3)
    label["Config"]["ControlBindings"] = [feedback(find_control(catalog, "SYN_READOUT"), "Text", "return String(value || '').replace(/\\u0000/g, '');")]
    page_id = str(uuid.uuid4())
    value = {"Id": str(uuid.uuid4()), "Title": "DCS DBMM synthetic example", "Author": "MATRIC Deck Skill", "DeckFileVersion": deck.CATALOG["deck_file_version"],
             "Description": "Training fixture only. SYN_ identifiers do not control a real DCS aircraft. Replace them using installed aircraft definitions.",
             "DefaultPageId": page_id, "ReferencedUserVariables": [],
             "Pages": [{"Id": page_id, "Title": "Training only", "Cols": 6, "Rows": 4, "BackgroundColor": "#111827",
                        "BackgroundImage": None, "BackgroundSize": "cover", "Controls": [button, switch, slider, label]}]}
    ensure_mailbox(value)
    result = audit(value, {}, catalog)
    if result["errors"]:
        raise ValueError("Invalid example: " + "; ".join(result["errors"]))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "deck2.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main():
    """Provide offline inventory, audit and synthetic example commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("inventory")
    inventory.add_argument("source", type=Path)
    inventory.add_argument("--aircraft")
    inventory.add_argument("--control")
    inventory.add_argument("--module")
    inventory.add_argument("--search")
    check = commands.add_parser("check")
    check.add_argument("source", type=Path)
    check.add_argument("--definitions", type=Path, required=True)
    check.add_argument("--aircraft")
    demo = commands.add_parser("example")
    demo.add_argument("--output", type=Path, required=True)
    for command in (inventory, check):
        command.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "example":
        result = example(args.output)
    elif args.command == "inventory" and args.source.is_dir() and not args.aircraft:
        if args.control or args.search or args.module:
            raise ValueError("Choose --aircraft before searching controls in a directory")
        result = {"modules": sorted(p.stem for p in args.source.glob("*.json") if p.name != "AircraftAliases.json"),
                  "aircraft_aliases": read(args.source / "AircraftAliases.json") if (args.source / "AircraftAliases.json").exists() else {}}
    else:
        catalog = load_definitions(args.definitions if args.command == "check" else args.source, args.aircraft)
        if args.command == "check":
            value, files = deck.load_deck(args.source)
            result = audit(value, files, catalog)
        elif args.control:
            result = find_control(catalog, args.control, args.module)
        else:
            result = copy.deepcopy(catalog)
            if args.module:
                if args.module not in catalog["modules"]:
                    raise ValueError("Selected module is not loaded for this aircraft")
                result["controls"] = [c for c in result["controls"] if c["module"] == args.module]
            if args.search:
                result["controls"] = [c for c in result["controls"] if args.search.casefold() in (c["identifier"] + " " + c["description"] + " " + c["category"]).casefold()]
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.command != "example" and args.output:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(text + "\n")
    else:
        print(text)
    if result.get("errors"):
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
