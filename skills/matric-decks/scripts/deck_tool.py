#!/usr/bin/env python3
"""Inspect, validate and package offline MATRIC decks using only Python's standard library."""
import argparse
import copy
import json
import math
import re
import sys
import uuid
import zipfile
from pathlib import Path, PurePosixPath

SKILL = Path(__file__).resolve().parents[1]
CATALOG = json.loads((SKILL / "references/catalog.json").read_text(encoding="utf-8-sig"))
ACTION_PREFIX = "EXM.MatricPro.Actions."
MAX_PAGE_DIMENSION = 50


def read_json(data):
    """Reject duplicate keys and non-JSON numeric literals rather than silently changing a deck."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f"Non-JSON number: {value}")
    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)


def safe_name(name):
    """Check portable archive paths, including names interpreted specially by Windows."""
    if not isinstance(name, str) or not name or name.startswith(("/", "\\")):
        raise ValueError(f"Invalid resource path: {name!r}")
    normalized = name.replace("\\", "/")
    for part in normalized.rstrip("/").split("/"):
        if not part or part in (".", "..") or re.search(r'[<>:"|?*\x00-\x1f]', part) or part.endswith((".", " ")):
            raise ValueError(f"Invalid resource path: {name!r}")
        if part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
            raise ValueError(f"Reserved Windows filename: {name!r}")
    return normalized.rstrip("/")


def load_deck(source):
    """Read a staged deck directory, deck2.json or .deck ZIP without extracting an archive."""
    source = Path(source)
    files = {}
    if source.is_dir() or source.name == "deck2.json":
        root = source if source.is_dir() else source.parent
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Linked resource is unsupported: {path}")
            if path.is_file():
                files[safe_name(path.relative_to(root).as_posix())] = path.read_bytes()
        if "deck2.json" not in files:
            raise ValueError("The staged folder must contain deck2.json directly.")
        deck = read_json(files["deck2.json"])
    else:
        with zipfile.ZipFile(source) as archive:
            roots = set()
            folded = set()
            for entry in archive.infolist():
                name = safe_name(entry.filename)
                roots.add(name.split("/")[0])
                if entry.is_dir():
                    continue
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Linked archive resources are unsupported.")
                if name.casefold() in folded:
                    raise ValueError(f"Duplicate archive path: {name}")
                folded.add(name.casefold())
                files[name] = archive.read(entry)
            if len(roots) != 1:
                raise ValueError("A .deck archive must have exactly one outer deck-ID folder.")
            outer = next(iter(roots))
            filename = outer + "/deck2.json"
            if filename not in files:
                raise ValueError("Expected <deck-id>/deck2.json, not deck.json or a root-level JSON file.")
            deck = read_json(files[filename])
            if not isinstance(deck, dict):
                raise ValueError("Deck must be a JSON object")
            if deck.get("Id") != outer:
                raise ValueError("The archive's outer folder must match deck.Id.")
            files = {name[len(outer) + 1:]: data for name, data in files.items()}
    folded = [name.casefold() for name in files]
    if len(set(folded)) != len(folded):
        raise ValueError("Resource paths collide on a case-insensitive filesystem.")
    return deck, files


def check_value(value, schema, where, errors):
    """Check serialized field types and enum values against the exported MATRIC catalog."""
    if value is None:
        if not schema.get("nullable", False):
            errors.append(f"{where}: null is invalid")
        return
    kind = schema["type"]
    matches = {"any": True, "string": isinstance(value, str), "integer": type(value) is int,
               "number": type(value) in (int, float) and math.isfinite(value),
               "boolean": type(value) is bool, "array": isinstance(value, list), "object": isinstance(value, dict)}
    if not matches.get(kind, False):
        errors.append(f"{where}: expected {kind}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: expected one of {schema['enum']}")
    if kind == "array":
        for i, item in enumerate(value):
            check_value(item, schema["items"], f"{where}[{i}]", errors)
    elif kind == "object":
        check_fields(value, schema.get("properties", {}), where, errors)


def check_fields(value, properties, where, errors):
    """Catch misspelled configuration fields while permitting MATRIC's computed serialization fields."""
    for key, item in value.items():
        if key in properties:
            check_value(item, properties[key], f"{where}.{key}", errors)
        elif key not in ("FileResources", "ActionType", "ActionTypeName"):
            errors.append(f"{where}.{key}: field absent from the bundled catalog")


def validate(deck, files, applets=None):
    """Check deck structure, event/action compatibility, navigation, geometry and bundled native resources."""
    errors, warnings = [], []
    if not isinstance(deck, dict):
        return {"errors": ["Deck must be a JSON object"], "warnings": []}
    try:
        if "/" in safe_name(deck.get("Id")):
            errors.append("Deck.Id must be a single folder name")
    except ValueError as error:
        errors.append(str(error))
    if type(deck.get("DeckFileVersion")) is not int or not 2 <= deck["DeckFileVersion"] <= CATALOG["deck_file_version"]:
        errors.append("Unsupported or missing DeckFileVersion; refresh the catalog for newer formats")
    pages = deck.get("Pages")
    if not isinstance(pages, list) or not pages:
        return {"errors": errors + ["Pages must be a nonempty array"], "warnings": warnings}
    ids, page_ids, navigation = set(), set(), []
    def identity(item, where):
        value = item.get("Id")
        if not isinstance(value, str) or not value:
            errors.append(f"{where}: missing Id")
        elif value in ids:
            errors.append(f"{where}: duplicate Id {value}")
        else:
            ids.add(value)
    def resources(value, where, properties):
        if isinstance(value, dict):
            for key, item in value.items():
                schema = properties.get(key, {})
                if schema.get("type") == "string" and (key.endswith("Image") or key.endswith("ImageActive") or key == "AudioFileName") and item:
                    try:
                        name = safe_name(item)
                        if name not in files:
                            errors.append(f"{where}.{key}: missing resource {name}")
                    except ValueError as error:
                        errors.append(str(error))
                elif key == "SwitchStateImages" and isinstance(item, list):
                    for i, image in enumerate(item):
                        resources({"Image": image}, f"{where}.{key}[{i}]", {"Image": {"type": "string"}})
                elif schema.get("type") == "object":
                    resources(item, f"{where}.{key}", schema.get("properties", {}))
                elif schema.get("type") == "array" and isinstance(item, list) and schema["items"].get("type") == "object":
                    for i, child in enumerate(item):
                        resources(child, f"{where}.{key}[{i}]", schema["items"].get("properties", {}))
    for pi, page in enumerate(pages):
        where = f"Pages[{pi}]"
        if not isinstance(page, dict):
            errors.append(f"{where}: expected object"); continue
        identity(page, where)
        resources(page, where, {"BackgroundImage": {"type": "string"}})
        if isinstance(page.get("Id"), str):
            page_ids.add(page["Id"])
        grid = all(type(page.get(key)) is int and page[key] > 0 for key in ("Cols", "Rows"))
        if not grid:
            errors.append(f"{where}: Cols and Rows must be positive integers")
        elif page["Cols"] > MAX_PAGE_DIMENSION or page["Rows"] > MAX_PAGE_DIMENSION:
            errors.append(f"{where}: Cols and Rows must not exceed {MAX_PAGE_DIMENSION} (supported page limit)")
        controls = page.get("Controls")
        if not isinstance(controls, list):
            errors.append(f"{where}.Controls: expected array"); continue
        boxes = []
        for ci, control in enumerate(controls):
            loc = f"{where}.Controls[{ci}]"
            if not isinstance(control, dict):
                errors.append(f"{loc}: expected object"); continue
            identity(control, loc)
            definition = next((v for v in CATALOG["controls"].values() if v["template"]["ControlTypeName"] == control.get("ControlTypeName")), None)
            if not definition:
                errors.append(f"{loc}: unknown ControlTypeName"); continue
            if control.get("ControlConfigTypeName") != definition["template"]["ControlConfigTypeName"]:
                errors.append(f"{loc}: ControlConfigTypeName does not match its control")
            geometry = all(type(control.get(key)) is int and control[key] >= (1 if key in ("Width", "Height") else 0) for key in ("X", "Y", "Width", "Height"))
            if not geometry:
                errors.append(f"{loc}: invalid grid-cell geometry")
            elif grid:
                x, y, width, height = (control[k] for k in ("X", "Y", "Width", "Height"))
                if x + width > page["Cols"] or y + height > page["Rows"]:
                    errors.append(f"{loc}: extends beyond page bounds")
                for bx, by, bw, bh, other in boxes:
                    if x < bx + bw and bx < x + width and y < by + bh and by < y + height:
                        warnings.append(f"{loc}: overlaps {other}; confirm this is intentional")
                boxes.append((x, y, width, height, loc))
            config = control.get("Config")
            event_definitions = definition["events"]
            if not isinstance(config, dict):
                errors.append(f"{loc}.Config: expected object")
            else:
                check_fields(config, definition["properties"], loc + ".Config", errors)
                resources(config, loc + ".Config", definition["properties"])
                if config.get("FontFace") not in (None, "text", "icon"):
                    warnings.append(f"{loc}: custom font must be installed separately")
                if control.get("ControlTypeName", "").endswith(".MCCustom"):
                    applet_identity = config.get("AppletId")
                    manifest = applets.get(applet_identity) if applets is not None and isinstance(applet_identity, str) else None
                    if manifest is None:
                        message = f"{loc}: applet {applet_identity!r} needs a separately installed applet and its manifest for event/parameter validation"
                        (errors if applets is not None else warnings).append(message)
                    else:
                        event_definitions = {}
                        for event in manifest["EventsDefinition"]:
                            allowed = {}
                            for name in event["AllowedActions"]:
                                full = name if name.startswith(ACTION_PREFIX) else ACTION_PREFIX + name
                                matches = [key for key, meta in CATALOG["actions"].items() if meta["action_id"] == full]
                                if len(matches) != 1:
                                    errors.append(f"{loc}: unknown applet runtime ActionId {name}")
                                    continue
                                # The custom-event editor exposes manifest actions without native-event cardinality flags.
                                allowed[matches[0]] = {"exclusive": False, "single": False, "implicit": False}
                            event_definitions[event["Name"]] = allowed
                        parameters = config.get("AppletParams")
                        if parameters is None:
                            parameters = {}
                        if not isinstance(parameters, dict):
                            errors.append(f"{loc}.Config.AppletParams: expected object")
                        else:
                            schemas = {}
                            for parameter in manifest["AppletParams"]:
                                kind = parameter["ParamType"]
                                schema = {"type": {"bool": "boolean", "number": "number"}.get(kind, "string"), "nullable": True}
                                if kind == "list":
                                    schema["enum"] = [option["Value"] for option in parameter["ListItems"]]
                                schemas[parameter["Name"]] = schema
                            for name, parameter_value in parameters.items():
                                parameter_location = loc + ".Config.AppletParams." + name
                                if name not in schemas:
                                    errors.append(f"{parameter_location}: field absent from the applet manifest")
                                else:
                                    check_value(parameter_value, schemas[name], parameter_location, errors)
            events = control.get("ControlEvents")
            if not isinstance(events, list):
                errors.append(f"{loc}.ControlEvents: expected array"); continue
            seen_events = set()
            for event in events:
                if not isinstance(event, dict) or not isinstance(event.get("Actions"), list):
                    errors.append(f"{loc}: invalid event configuration"); continue
                name = event.get("Name")
                if not isinstance(name, str):
                    errors.append(f"{loc}: invalid event name"); continue
                if name in seen_events:
                    errors.append(f"{loc}: duplicate event {name}")
                seen_events.add(name)
                allowed = event_definitions.get(name)
                if allowed is None:
                    errors.append(f"{loc}: event {name!r} absent from the catalog; applet events need an applet manifest")
                    continue
                action_types = []
                for action in event["Actions"]:
                    if not isinstance(action, dict):
                        errors.append(f"{loc}/{name}: invalid action"); continue
                    action_type = action.get("ActionTypeName")
                    if not isinstance(action_type, str) or action_type not in CATALOG["actions"]:
                        errors.append(f"{loc}/{name}: unknown ActionTypeName"); continue
                    action_types.append(action_type)
                    metadata = CATALOG["actions"][action_type]
                    check_fields(action, metadata["properties"], f"{loc}/{name}/{action_type}", errors)
                    resources(action, f"{loc}/{name}/{action_type}", metadata["properties"])
                    if action_type not in allowed:
                        errors.append(f"{loc}/{name}: incompatible action {action_type}")
                    elif allowed[action_type]["exclusive"] and len(event["Actions"]) != 1:
                        errors.append(f"{loc}/{name}: {action_type} must be the only action")
                    if action_type.endswith(".ActionGoToPage"):
                        navigation.append((action.get("TargetPageId"), loc))
                    if action_type.endswith(".ActionHotkey"):
                        if type(action.get("KeyCode")) is not int or not 0 < action["KeyCode"] <= 65535:
                            errors.append(f"{loc}: hotkeys require an explicit valid KeyCode")
                        for modifier in action.get("Modifiers", []) if isinstance(action.get("Modifiers"), list) else []:
                            if not isinstance(modifier, str) or modifier not in CATALOG["key_codes"]:
                                errors.append(f"{loc}: unsupported modifier {modifier}")
                    if action_type.endswith(".ActionStreamDeckContainer"):
                        warnings.append(f"{loc}: experimental plugin settings/resources require separate MATRIC compatibility verification")
                for action_type in set(action_types):
                    if action_type in allowed and allowed[action_type]["single"] and action_types.count(action_type) > 1:
                        errors.append(f"{loc}/{name}: duplicate single-instance action {action_type}")
    if not isinstance(deck.get("DefaultPageId"), str) or deck["DefaultPageId"] not in page_ids:
        errors.append("DefaultPageId does not identify a page")
    for target, loc in navigation:
        if not isinstance(target, str) or target not in page_ids:
            errors.append(f"{loc}: TargetPageId does not identify a page")
    return {"errors": errors, "warnings": list(dict.fromkeys(warnings))}


def new_control(kind, text, x, y, width=1, height=1):
    """Copy exact runtime defaults, add a fresh identity and supply a readable native appearance."""
    control = copy.deepcopy(CATALOG["controls"][kind]["template"])
    control.update(Id=str(uuid.uuid4()), Name="", Text=text, X=x, Y=y, Width=width, Height=height)
    appearance = dict(FontFace="text", TextSize=22, Padding=4, Halign="center", Valign="mid",
                      TextColor="#ffffff", TextColorActive="#ffffff", BackgroundColor="#263449", BackgroundColorActive="#4169e1")
    control["Config"].update({key: value for key, value in appearance.items() if key in control["Config"]})
    if kind == "MCSlider":
        control["Config"].update(TrackColorBackground="#111827", TrackColorFilled="#38bdf8", ShowValue=True)
    if kind == "MCTouchpad":
        # The runtime constructor retains an old event name; the definition and client emit "touchpad".
        for event in control["ControlEvents"]:
            if event["Name"] == "valuechange":
                event["Name"] = "touchpad"
    return control


def action_metadata(name):
    """Resolve serialized implementation names, retaining compatibility with older catalog action IDs."""
    name = name if name.startswith(ACTION_PREFIX) else ACTION_PREFIX + name
    if name in CATALOG["actions"]:
        return CATALOG["actions"][name]
    found = [v for v in CATALOG["actions"].values() if v.get("action_id") == name]
    if len(found) != 1:
        raise KeyError(name)
    return found[0]


def action(name, **values):
    """Create an action from the bundled template without guessing its serialized field names."""
    result = copy.deepcopy(action_metadata(name)["template"])
    if "StreamDeckInstanceId" in result:
        result["StreamDeckInstanceId"] = uuid.uuid4().hex
    result.update(values)
    return result


def main():
    """Provide offline catalog inspection, draft creation, validation, extraction and package creation."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog")
    catalog.add_argument("--control"); catalog.add_argument("--action")
    new = commands.add_parser("new")
    new.add_argument("--title", required=True); new.add_argument("--author", default="")
    new.add_argument("--cols", type=int, default=6); new.add_argument("--rows", type=int, default=4)
    new.add_argument("--output", type=Path, required=True)
    for verb in ("validate", "pack", "unpack"):
        command = commands.add_parser(verb)
        command.add_argument("source", type=Path)
        command.add_argument("--applet", action="append", type=Path, default=[],
                             help="Explicit applet folder/.mapl for manifest-aware checks; repeat for several applets")
        if verb != "validate":
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "catalog":
        if args.control:
            result = CATALOG["controls"][args.control]
        elif args.action:
            result = action_metadata(args.action)
        else:
            result = {"deck_file_version": CATALOG["deck_file_version"], "controls": {k: v["description"] for k, v in CATALOG["controls"].items()},
                      "actions": {k: v["description"] for k, v in CATALOG["actions"].items()}}
        print(json.dumps(result, ensure_ascii=False, indent=2)); return
    if args.command == "new":
        if not (1 <= args.cols <= MAX_PAGE_DIMENSION and 1 <= args.rows <= MAX_PAGE_DIMENSION):
            parser.error(f"Grid dimensions must be integers from 1 to {MAX_PAGE_DIMENSION}")
        page_id = str(uuid.uuid4())
        deck = {"Id": str(uuid.uuid4()), "Title": args.title, "Author": args.author, "Description": "",
                "DeckFileVersion": CATALOG["deck_file_version"], "DefaultPageId": page_id, "ReferencedUserVariables": [],
                "Pages": [{"Id": page_id, "Title": "Main", "Cols": args.cols, "Rows": args.rows, "BackgroundColor": "#111827",
                           "BackgroundImage": None, "BackgroundSize": "cover", "Controls": []}]}
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "deck2.json").write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
        print(args.output / "deck2.json"); return
    deck, files = load_deck(args.source)
    applets = None
    if args.applet:
        from applet_tool import load_manifests
        applets = load_manifests(args.applet)
    report = validate(deck, files, applets)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["errors"]:
        raise SystemExit(1)
    if args.command == "pack":
        output = args.output.resolve()
        root = args.source.resolve().parent if args.source.is_file() else args.source.resolve()
        if output == root or root in output.parents:
            raise ValueError("Write the archive outside the staged deck directory")
        if output.suffix.lower() != ".deck":
            raise ValueError("Package filename must end in .deck")
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(files.items()):
                archive.writestr(deck["Id"] + "/" + name, content)
        print(output)
    elif args.command == "unpack":
        args.output.mkdir(parents=True, exist_ok=False)
        for name, content in files.items():
            destination = args.output / PurePosixPath(name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        print(args.output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
