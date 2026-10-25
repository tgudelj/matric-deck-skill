#!/usr/bin/env python3
"""Author, validate and package portable MATRIC custom applets; never install or execute them."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import sys
import uuid
import zipfile

import deck_tool as deck

MAX_BYTES = 128 * 1024 * 1024
MAX_FILES = 4096
TEMPLATE = deck.SKILL / "assets/applet-starter"
PARAM_TYPES = {"string", "number", "bool", "list", "variable", "color"}


def applet_id(value):
    """Check the explicit ID used by the applet importer and custom-library folder."""
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", value):
        raise ValueError("AppletId must contain 1..128 letters, digits, underscores or hyphens")
    deck.safe_name(value)
    return value


def canonical(value, names, where):
    """Normalize compatible property casing while rejecting case-ambiguous metadata."""
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    keys = {name.lower(): name for name in names}
    result = {}
    seen = set()
    for name, item in value.items():
        if name.lower() in seen:
            raise ValueError(f"{where}: ambiguous property casing for {name}")
        seen.add(name.lower())
        if name.lower() not in keys:
            raise ValueError(f"{where}: unknown field {name}")
        result[keys[name.lower()]] = item
    return result


def runtime_action(name):
    """Resolve manifest AllowedActions by runtime ActionId, distinct from serialized type names."""
    if not isinstance(name, str):
        raise ValueError("AllowedActions must contain runtime action-name strings")
    full = name if name.startswith(deck.ACTION_PREFIX) else deck.ACTION_PREFIX + name
    matches = [key for key, item in deck.CATALOG["actions"].items() if item["action_id"] == full]
    if len(matches) != 1:
        raise ValueError(f"Unknown runtime ActionId {name!r}; use catalog action_id, not an assumed serialized name")
    return matches[0]


def parameter_value(value, parameter):
    """Check portable authored parameter values; this does not prove variable availability."""
    kind = parameter["ParamType"]
    if value is None:
        return True  # Native manifests allow unset/defaulted parameters.
    if kind == "number":
        return type(value) in (int, float) and math.isfinite(value)
    if kind == "bool":
        return type(value) is bool
    if not isinstance(value, str):
        return False
    if kind == "list":
        return value in [item["Value"] for item in parameter["ListItems"]]
    return True


def manifest(data):
    """Normalize and validate an explicit authoring manifest against the inspected format."""
    data = canonical(data, ("AppletId", "DisplayName", "Description", "Author", "VersionMajor", "VersionMinor",
                            "AppletParams", "EventsDefinition"), "manifest")
    applet_id(data.get("AppletId"))
    for name in ("DisplayName", "Description", "Author"):
        data.setdefault(name, "")
        if not isinstance(data[name], str):
            raise ValueError(f"{name} must be a string")
    if not data["DisplayName"].strip():
        raise ValueError("DisplayName must describe the applet")
    for name in ("VersionMajor", "VersionMinor"):
        data.setdefault(name, 0)
        if type(data[name]) is not int or data[name] < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    for collection in ("AppletParams", "EventsDefinition"):
        if data.get(collection) is None:
            data[collection] = []
        if not isinstance(data[collection], list):
            raise ValueError(f"{collection} must be an array")
        seen = set()
        normalized = []
        for item in data[collection]:
            fields = ("Name", "DisplayName", "ParamType", "Default", "ListItems") if collection == "AppletParams" else ("Name", "DisplayName", "Description", "AllowedActions")
            item = canonical(item, fields, collection)
            name = item.get("Name")
            if not isinstance(name, str) or not name.strip() or name in seen:
                raise ValueError(f"{collection}: each Name must be nonempty and unique")
            seen.add(name)
            item.setdefault("DisplayName", name)
            if not isinstance(item["DisplayName"], str):
                raise ValueError(f"{name}: DisplayName must be a string")
            if collection == "AppletParams":
                item.setdefault("ParamType", "string")
                if item["ParamType"] not in PARAM_TYPES:
                    raise ValueError(f"{name}: unsupported ParamType")
                options = item.get("ListItems")
                if options is None:
                    options = []
                if not isinstance(options, list):
                    raise ValueError(f"{name}: ListItems must be an array")
                item["ListItems"] = []
                values = set()
                for option in options:
                    option = canonical(option, ("Text", "Value"), f"{name}.ListItems")
                    value = option.get("Value")
                    if not isinstance(value, str) or value in values:
                        raise ValueError(f"{name}: list values must be unique strings")
                    values.add(value)
                    option.setdefault("Text", value)
                    if not isinstance(option["Text"], str):
                        raise ValueError(f"{name}: list Text must be a string")
                    item["ListItems"].append(option)
                if not parameter_value(item.get("Default"), item):
                    raise ValueError(f"{name}: Default does not match ParamType/list choices")
            else:
                if "Description" in item and not isinstance(item["Description"], str):
                    raise ValueError(f"{name}: event Description must be a string")
                if name in ("reqvariables", "__cancel_applet_inputs") or name.endswith("-release"):
                    raise ValueError(f"{name}: reserved protocol/lifecycle event name")
                actions = item.get("AllowedActions")
                if actions is None:
                    actions = []
                if not isinstance(actions, list):
                    raise ValueError(f"{name}: AllowedActions must be an array")
                for action in actions:
                    runtime_action(action)
                item["AllowedActions"] = list(dict.fromkeys(actions))
            normalized.append(item)
        data[collection] = normalized
    return data


def _file_name(name):
    name = deck.safe_name(name)
    if len(name.split("/")) > 16:
        raise ValueError("Applet package path exceeds the 16-component limit")
    return name


def load(source):
    """Read a folder or root/one-folder .mapl ZIP without extracting or running any code."""
    source = Path(source)
    files = {}
    total = 0

    def retain(name, size, read):
        nonlocal total
        name = _file_name(name)
        if name.casefold() in {key.casefold() for key in files}:
            raise ValueError(f"Duplicate/case-colliding applet path: {name}")
        total += size
        if name.split("/")[-1].lower() == "manifest.json" and size > 1024 * 1024:
            raise ValueError("manifest.json exceeds 1 MiB")
        if len(files) >= MAX_FILES or total > MAX_BYTES:
            raise ValueError("Applet exceeds 4096 files or 128 MiB expanded size")
        content = read()
        if len(content) != size:
            raise ValueError("Incomplete applet resource")
        files[name] = content

    if source.is_dir():
        if source.is_symlink():
            raise ValueError("Linked applet root is unsupported")
        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                raise ValueError("Linked applet resources are unsupported")
            if path.is_file():
                retain(path.relative_to(source).as_posix(), path.stat().st_size, path.read_bytes)
    else:
        with zipfile.ZipFile(source) as archive:
            if len(archive.infolist()) > MAX_FILES:
                raise ValueError("Applet archive exceeds 4096 entries")
            seen = set()
            for entry in archive.infolist():
                name = _file_name(entry.filename)
                if name.casefold() in seen:
                    raise ValueError("Duplicate/case-colliding applet archive entry")
                seen.add(name.casefold())
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Linked archive resources are unsupported")
                if not entry.is_dir():
                    retain(name, entry.file_size, lambda entry=entry: archive.read(entry))
    manifests = [name for name in files if name.split("/")[-1].lower() == "manifest.json"]
    if len(manifests) != 1:
        raise ValueError("Applet must have exactly one manifest.json")
    metadata = manifests[0]
    if len(files[metadata]) > 1024 * 1024:
        raise ValueError("manifest.json exceeds 1 MiB")
    root = metadata[:-len("manifest.json")]
    if root.count("/") > 1 or any(not name.startswith(root) for name in files):
        raise ValueError("Applet files must be at root or in one immediate folder, with no outside files")
    files = {name[len(root):]: content for name, content in files.items()}
    if "manifest.json" not in files or not files.get("applet.html", b"").strip():
        raise ValueError("Expected manifest.json and nonempty applet.html with exact filename casing")
    return manifest(deck.read_json(files["manifest.json"])), files


def validate(source):
    """Check metadata and local HTML/CSS asset references, without interpreting JavaScript."""
    data, files = load(source)
    warnings = []
    from html.parser import HTMLParser
    from urllib.parse import unquote, urlsplit

    def resource(reference, owner):
        if reference.startswith("#") or not reference:
            return
        url = urlsplit(reference)
        if url.scheme or url.netloc or reference.startswith("/"):
            if not reference.startswith("data:"):
                warnings.append(f"{owner}: external/root resource {reference!r} needs separate availability/security review")
            return
        # References inside bundled CSS/HTML resolve relative to the referring file.
        import posixpath
        name = posixpath.normpath(posixpath.join(posixpath.dirname(owner), unquote(url.path)))
        _file_name(name)
        if name not in files:
            raise ValueError(f"{owner}: missing local resource {name}")

    class Resources(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            for attr in ("src", "poster"):
                if attrs.get(attr):
                    resource(attrs[attr], self.owner)
            if tag == "link" and attrs.get("href"):
                resource(attrs["href"], self.owner)
            if tag == "base":
                warnings.append(f"{self.owner}: HTML base URL requires manual resource review")

    for name, content in files.items():
        if name.lower().endswith((".html", ".css")):
            text = content.decode("utf-8-sig")
            if name.lower().endswith(".html"):
                parser = Resources()
                parser.owner = name
                parser.feed(text)
            for reference in re.findall(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", text):
                resource(reference.strip(), name)
        if name.lower().endswith((".ttf", ".otf", ".woff", ".woff2")):
            raise ValueError("Fonts must be obtained separately and installed in MATRIC's fonts directory")
    return {"applet_id": data["AppletId"], "errors": [], "warnings": list(dict.fromkeys(warnings))}


def load_manifests(sources):
    """Load explicitly supplied applets; never scan the user's live applet library."""
    result = {}
    for source in sources:
        validate(source)
        data, _ = load(source)
        if data["AppletId"] in result:
            raise ValueError("Duplicate supplied AppletId: " + data["AppletId"])
        result[data["AppletId"]] = data
    return result


def pack(source, output):
    """Create a deterministic root-layout .mapl package; refuse overwrite or nested output."""
    report = validate(source)
    _, files = load(source)
    output = Path(output).resolve()
    root = Path(source).resolve()
    if output.suffix.lower() != ".mapl" or output == root or root in output.parents:
        raise ValueError("Choose a .mapl output outside the applet source directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return report


def new(output, identity, title):
    """Copy the original, self-contained history-inspector starter with an explicit identity."""
    applet_id(identity)
    output = Path(output)
    if output.exists():
        raise FileExistsError("Choose a new applet staging folder")
    data = manifest(deck.read_json((TEMPLATE / "manifest.json").read_bytes()))
    data.update(AppletId=identity, DisplayName=title)
    data = manifest(data)
    shutil.copytree(TEMPLATE, output)
    (output / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def example(output):
    """Build a synthetic applet, integrated demo deck and separate importable deliverables."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    identity = "skill-history-" + uuid.uuid4().hex[:12]
    data = new(output / "applet", identity, "History inspector demo")
    control = deck.new_control("MCCustom", "History", 0, 0, 12, 17)
    control.update(Name="history_inspector")
    control["Config"].update(AppletId=identity, AllowedFeatures="", AppletParams={"SignalVariable": "skill_demo_signal"})
    control["ControlEvents"] = [{"Name": "select-sample", "Actions": [deck.action("ActionSetServerVariable",
        VariableName="skill_demo_selection", VariableType="NUMBER", VariableValue=0,
        VariableCalculateValueFunction="var n = Number(eventData.value); return Number.isFinite(n) ? n : 0;")]}]
    controls = [control]
    for i, (label, value) in enumerate((("LOW", 0), ("MID", 50), ("HIGH", 100))):
        button = deck.new_control("MCButton", label, i * 4, 18, 4, 3)
        button["ControlEvents"] = [{"Name": "release", "Actions": [deck.action("ActionSetServerVariable",
            VariableName="skill_demo_signal", VariableType="NUMBER", VariableValue=value)]}]
        controls.append(button)
    selected = deck.new_control("MCButton", "Selected: waiting", 0, 22, 12, 3)
    selected["Config"]["ControlBindings"] = [{"PropertyPath": "Text", "VariableName": "skill_demo_selection",
        "Transform": "return value == null ? 'Selected: waiting' : 'Selected: ' + String(value);"}]
    controls.append(selected)
    page_id = str(uuid.uuid4())
    value = {"Id": str(uuid.uuid4()), "Title": "Applet history demo", "Author": "MATRIC Deck Skill",
        "Description": "Explore a signal's recent history and tap a sample to select it. Synthetic example for an approximately 6-inch phone in portrait, 9:19.5 aspect ratio. Import the accompanying applet and create the two demo number variables before use.",
        "DeckFileVersion": deck.CATALOG["deck_file_version"], "DefaultPageId": page_id, "ReferencedUserVariables": [],
        "Pages": [{"Id": page_id, "Title": "History", "Cols": 12, "Rows": 26, "BackgroundColor": "#101827",
                   "BackgroundImage": None, "BackgroundSize": "cover", "Controls": controls}]}
    staged = output / "deck"
    staged.mkdir()
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    (staged / "deck2.json").write_text(text, encoding="utf-8")
    report = deck.validate(value, {"deck2.json": text.encode()}, {identity: data})
    if report["errors"]:
        raise ValueError(str(report))
    pack(output / "applet", output / "History.mapl")
    with zipfile.ZipFile(output / "History.deck", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(value["Id"] + "/deck2.json", text.encode())
    (output / "SETUP.txt").write_text(
        "History inspector demo\n\n1. Open History.mapl with MATRIC to install the applet. Import History.deck.\n"
        "2. In MATRIC's Variables dialog create NUMBER variables skill_demo_signal and skill_demo_selection, both initially 0.\n"
        "3. On the client tap LOW/MID/HIGH to build history. Tap the trace to select a sample; the native readout shows it.\n"
        "The demo changes only those synthetic variables. It does not connect to OBS/DCS or execute system inputs.\n"
        "The applet installs under Documents/MATRIC/custom/<AppletId>. Importing the same ID replaces its installed files.\n"
        "Static validation and preview do not prove native import or device behavior.\n", encoding="utf-8")
    return {"applet_id": identity, "errors": [], "warnings": report["warnings"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("new")
    create.add_argument("--id", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--output", required=True, type=Path)
    for verb in ("validate", "pack"):
        sub = commands.add_parser(verb)
        sub.add_argument("source", type=Path)
        if verb == "pack":
            sub.add_argument("--output", required=True, type=Path)
    demo = commands.add_parser("example")
    demo.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "new":
        new(args.output, args.id, args.title)
        report = validate(args.output)
    elif args.command == "example":
        report = example(args.output)
    elif args.command == "pack":
        report = pack(args.source, args.output)
    else:
        report = validate(args.source)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
