#!/usr/bin/env python3
"""Read simulator input profiles and propose native MATRIC actions; never send input.

Supports explicit Star Citizen rebinds, Elite Dangerous .binds, and readable
MSFS 2020/2024 XML profiles. Reports preserve source semantics for author review.
"""
import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from deck_tool import action

MAX_BYTES = 16 * 1024 * 1024
GAMES = ("msfs2020", "msfs2024", "starcitizen", "elite")
MODIFIERS = {"lctrl": (162, "LCONTROL"), "rctrl": (163, "RCONTROL"),
             "lcontrol": (162, "LCONTROL"), "rcontrol": (163, "RCONTROL"),
             "lshift": (160, "LSHIFT"), "rshift": (161, "RSHIFT"),
             "lalt": (164, "LALT"), "ralt": (165, "RALTGRAPH")}
KEYS = {"space": 32, "enter": 13, "return": 13, "escape": 27, "esc": 27,
        "tab": 9, "backspace": 8, "insert": 45, "delete": 46,
        "home": 36, "end": 35, "pageup": 33, "pagedown": 34,
        "pgup": 33, "pgdn": 34, "up": 38, "down": 40, "left": 37,
        "right": 39, "uparrow": 38, "downarrow": 40,
        "leftarrow": 37, "rightarrow": 39}
VK_MODIFIERS = {v[0]: v[1] for v in MODIFIERS.values()}
VK_MODIFIERS.update({16: "LSHIFT", 17: "LCONTROL", 18: "LALT"})


def read_xml(path, fragments=False):
    """Read bounded Unicode XML, including MSFS's adjacent top-level elements."""
    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Profile exceeds 16 MiB: " + str(path))
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    text = raw.decode(encoding)
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.I):
        raise ValueError("DTD/entity declarations are unsupported")
    text = re.sub(r"^\s*<\?xml[^?]*\?>", "", text, count=1)
    root = ET.fromstring("<ProfileFragment>" + text + "</ProfileFragment>" if fragments else text)
    if any("}" in node.tag for node in root.iter()):
        raise ValueError("Namespaced profile XML is unsupported")
    source = {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
              "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
    return root, source


def snapshot(node):
    """Preserve nested settings, including unknown timing/axis options, as data."""
    return {"tag": node.tag, "attributes": dict(node.attrib),
            "text": (node.text or "").strip(), "children": [snapshot(n) for n in node]}


def row(context, name, slot, device, tokens, modifiers=None, settings=None, unbound=False):
    return {"context": context, "action": name, "slot": slot, "device": device,
            "inputs": tokens, "modifiers": modifiers or [], "settings": settings or {},
            "unbound": unbound, "candidate": None, "warnings": []}


def parse_elite(root):
    if root.tag != "Root" or "PresetName" not in root.attrib:
        raise ValueError("Expected Elite .binds Root with PresetName")
    rows = []
    for command in root:
        slots = [n for n in command if n.tag in ("Primary", "Secondary", "Binding")]
        for slot in slots:
            device, key = slot.get("Device", ""), slot.get("Key", "")
            mods = [{"device": n.get("Device", ""), "key": n.get("Key", "")}
                    for n in slot.findall("Modifier")]
            settings = {"command": dict(command.attrib), "slot": dict(slot.attrib),
                        "options": [snapshot(n) for n in command if n not in slots]}
            rows.append(row("profile", command.tag, slot.tag, device, [key], mods,
                            settings, device == "{NoDevice}" or not key))
    return {"name": root.get("PresetName"), "attributes": dict(root.attrib),
            "keyboard_layout": root.findtext("KeyboardLayout")}, rows


def parse_sc(root):
    if root.tag not in ("ActionMaps", "ActionProfiles"):
        raise ValueError("Expected Star Citizen ActionMaps or ActionProfiles")
    maps = list(root.iter("actionmap"))
    rows = []
    for group in maps:
        for command in group.findall("action"):
            for i, bind in enumerate(command.findall("rebind")):
                raw = bind.get("input", "")
                match = re.match(r"(kb\d+|js\d+|gp\d+|mo\d+)_(.*)", raw)
                device, token = match.groups() if match else ("unknown", raw)
                settings = {"action": dict(command.attrib), "rebind": dict(bind.attrib),
                            "options": [snapshot(n) for n in command if n.tag != "rebind"]}
                rows.append(row(group.get("name", ""), command.get("name", ""),
                                "rebind-" + str(i), device, [token], settings=settings,
                                unbound=not token.strip()))
    metadata = {"attributes": dict(root.attrib),
                "profiles": [dict(n.attrib) for n in root.iter("ActionProfiles")],
                "devices": [snapshot(n) for n in root.iter("options")],
                "modifiers": [snapshot(n) for n in root.iter("modifiers")],
                "activation_modes": [snapshot(n) for n in root.iter("ActivationModes")]}
    return metadata, rows


def parse_msfs(root):
    devices = list(root.iter("Device"))
    if not devices:
        raise ValueError("Expected readable MSFS XML containing Device")
    rows = []
    for device in devices:
        identity = device.get("GUID") or device.get("DeviceName", "unknown")
        for context in device.findall("Context"):
            for command in context:
                if command.tag not in ("Action", "Actions"):
                    continue
                for slot in ("Primary", "Secondary"):
                    binding = command.find(slot)
                    keys = [n for n in binding if n.tag in ("KEY", "Key")] if binding is not None else []
                    values = [(n.text or "").strip() for n in keys]
                    settings = {"action": dict(command.attrib), "device": dict(device.attrib),
                                "keys": [dict(n.attrib) for n in keys],
                                "axis": snapshot(binding) if binding is not None else None}
                    rows.append(row(context.get("ContextName", ""), command.get("ActionName", ""),
                                    slot, identity, values, settings=settings, unbound=not values))
    return {"friendly_names": [n.text for n in root.iter("FriendlyName")],
            "versions": [dict(n.attrib) for n in root.iter("Version")],
            "devices": [dict(n.attrib) for n in devices],
            "aircraft": [dict(n.attrib) for n in root.iter("AircraftInfo")],
            "axis_settings": [snapshot(n) for n in root.iter("Axes")]}, rows


def key_code(token):
    token = token.lower().removeprefix("key_")
    token = {"leftcontrol": "lcontrol", "rightcontrol": "rcontrol",
             "leftshift": "lshift", "rightshift": "rshift",
             "leftalt": "lalt", "rightalt": "ralt"}.get(token, token)
    if token in MODIFIERS:
        return MODIFIERS[token][0]
    if len(token) == 1 and token.isascii() and token.isalnum():
        return ord(token.upper())
    if re.fullmatch(r"f(?:[1-9]|1\d|2[0-4])", token):
        return 111 + int(token[1:])
    if re.fullmatch(r"numpad[0-9]", token):
        return 96 + int(token[-1])
    return KEYS.get(token)


def keyboard_candidate(binding, game):
    """Translate only known keyboard tokens; preserve unfamiliar chords for review."""
    if game.startswith("msfs"):
        if binding["settings"]["device"].get("DeviceName", "").lower() != "keyboard":
            return None
        try:
            codes = [int(v) for v in binding["inputs"]]
            flag = int(binding["settings"]["action"].get("Flag", "0"))
        except ValueError:
            return None
        if flag & 16:
            codes.append(162)
        if flag & 32:
            codes.append(160)
        if flag & 64:
            codes.append(164)
    elif game == "elite":
        if binding["device"] != "Keyboard" or any(m["device"] != "Keyboard" for m in binding["modifiers"]):
            return None
        codes = [key_code(v) for v in binding["inputs"] + [m["key"] for m in binding["modifiers"]]]
    else:
        if not binding["device"].startswith("kb"):
            return None
        codes = [key_code(v) for v in binding["inputs"][0].split("+")]
    if any(v is None or not 1 <= v <= 255 for v in codes):
        return None
    main = [v for v in codes if v not in VK_MODIFIERS]
    if len(main) != 1:
        return None
    return action("ActionHotkey", KeyCode=main[0], Keystroke=str(main[0]),
                  Modifiers=list(dict.fromkeys(VK_MODIFIERS[v] for v in codes if v in VK_MODIFIERS)), Toggle=False)


def validate_devices(devices):
    """Validate explicit device correspondence/capabilities without accessing a driver."""
    if not isinstance(devices, dict):
        raise ValueError("Device map must be an object keyed by exact game device identity")
    for name, device in devices.items():
        if not isinstance(device, dict) or type(device.get("DeviceId")) is not int or not 1 <= device["DeviceId"] <= 16:
            raise ValueError("Invalid vJoy DeviceId for " + name)
        if type(device.get("buttons")) is not int or not 0 <= device["buttons"] <= 128:
            raise ValueError("buttons must be 0..128")
        if type(device.get("povs")) is not int or not 0 <= device["povs"] <= 4:
            raise ValueError("povs must be the configured discrete POV count, 0..4")
        if not isinstance(device.get("axes"), list) or any(type(v) is not int or v not in range(48, 56) for v in device["axes"]):
            raise ValueError("axes must list configured HID usage integers, 48..55")
        if not isinstance(device.get("inputs"), dict):
            raise ValueError("inputs must map exact profile tokens to vJoy targets")
        for spec in device["inputs"].values():
            if not isinstance(spec, dict):
                raise ValueError("Invalid vJoy input target")
            kind = spec.get("kind")
            if kind == "button":
                valid = type(spec.get("button")) is int and 1 <= spec["button"] <= device["buttons"]
            elif kind == "axis":
                valid = type(spec.get("axis")) is int and spec["axis"] in device["axes"] and type(spec.get("invert", False)) is bool
            elif kind == "pov":
                valid = type(spec.get("pov")) is int and 1 <= spec["pov"] <= device["povs"] and spec.get("direction") in ("N", "E", "S", "W")
            else:
                valid = False
            if not valid:
                raise ValueError("Target exceeds configured capabilities or has unsupported kind: " + name)


def vjoy_candidate(binding, devices):
    device = devices.get(binding["device"])
    if (not device or binding["modifiers"] or len(binding["inputs"]) != 1
            or "+" in binding["inputs"][0]):
        return None
    spec = device["inputs"].get(binding["inputs"][0])
    if not spec:
        return None
    common = {"DeviceId": device["DeviceId"]}
    if spec["kind"] == "button":
        return action("ActionVjoyButton", ButtonId=spec["button"], **common)
    if spec["kind"] == "axis":
        return action("ActionVJoyAxis", Axis=spec["axis"], InvertAxis=spec.get("invert", False), **common)
    return action("ActionVjoyPOV", POVId=spec["pov"], POVDirection=spec["direction"], **common)


def inventory(game, paths, devices=None, required=(), active_confirmed=False):
    devices = devices or {}
    validate_devices(devices)
    report = {"game": game, "input_only": True, "active_profiles_confirmed": active_confirmed,
              "sources": [], "profiles": [], "bindings": [], "conflicts": [],
              "missing_actions": [], "warnings": []}
    if game not in GAMES:
        raise ValueError("Unsupported game")
    if not active_confirmed:
        report["warnings"].append("Selected files are saved profiles; confirm their active selection in the game.")
    if game == "starcitizen":
        report["warnings"].append("Explicit rebinds only: omitted actions and default activation modes are unknown. Use matching-build defaults or in-game verification; do not assume absent means unbound.")
    if game.startswith("msfs"):
        report["warnings"].append("Profiles remain separate. Confirm general/category/aircraft layers; no precedence is inferred. MSFS flags, keyboard layout and axis curves require review.")
    for path in paths:
        root, source = read_xml(path, game.startswith("msfs"))
        metadata, rows = (parse_msfs(root) if game.startswith("msfs") else
                          parse_elite(root) if game == "elite" else parse_sc(root))
        index = len(report["sources"])
        report["sources"].append(source)
        report["profiles"].append(metadata)
        if not rows:
            report["warnings"].append("No supported binding entries in " + source["path"])
        for binding in rows:
            binding["source"] = index
            binding["id"] = str(index) + ":" + str(len(report["bindings"]))
            if not binding["action"]:
                raise ValueError("Binding lacks an action identifier")
            if not binding["unbound"]:
                binding["candidate"] = keyboard_candidate(binding, game) or vjoy_candidate(binding, devices)
                binding["warnings"].append("Review context, activation timing and hold/toggle semantics before choosing the MATRIC event. Local control state is not simulator feedback.")
                if not binding["candidate"]:
                    binding["warnings"].append("No automatic translation: inspect tokens/modifiers or confirm a vJoy device/input correspondence. Rebinding may be needed.")
            report["bindings"].append(binding)
    groups = {}
    for binding in report["bindings"]:
        if binding["unbound"]:
            continue
        candidate = binding["candidate"]
        if candidate:
            normalized = dict(candidate)
            normalized.pop("Keystroke", None)
            if "Modifiers" in normalized:
                normalized["Modifiers"] = sorted(normalized["Modifiers"])
            signature = (binding["context"], json.dumps(normalized, sort_keys=True))
        else:
            signature = (binding["context"], binding["device"], tuple(binding["inputs"]),
                         json.dumps(binding["modifiers"], sort_keys=True))
        groups.setdefault(signature, []).append(binding)
    for group in groups.values():
        if len({b["action"] for b in group}) > 1:
            report["conflicts"].append({"bindings": [b["id"] for b in group],
                                        "reason": "Shared input in selected profiles/context; review activation modes and profile precedence."})
    bound = {b["action"] for b in report["bindings"] if not b["unbound"]}
    report["missing_actions"] = sorted(set(required) - bound)
    return report


def discover(game, root):
    """List candidates only under an explicitly selected folder; never select by age."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("Discovery root must be a directory")
    results, warnings = [], []
    count = 0
    for path in root.rglob("*"):
        count += 1
        if count > 10000:
            warnings.append("Discovery stopped at 10000 entries; select a narrower root.")
            break
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        if game == "elite" and path.name.startswith("StartPreset") and path.suffix == ".start":
            if path.stat().st_size <= 4096:
                results.append({"path": str(path), "selected_presets": path.read_text(encoding="utf-8-sig").splitlines()})
            continue
        plausible = (path.suffix.lower() == ".binds" if game == "elite" else
                     path.suffix.lower() == ".xml" if game == "starcitizen" else
                     path.suffix.lower() == ".xml" or path.name.startswith("inputprofile_") or not path.suffix)
        if not plausible:
            continue
        try:
            root_node, _ = read_xml(path, game.startswith("msfs"))
            metadata, _ = (parse_msfs(root_node) if game.startswith("msfs") else
                           parse_elite(root_node) if game == "elite" else parse_sc(root_node))
            results.append({"path": str(path), "metadata": metadata})
        except (ValueError, OSError, ET.ParseError, UnicodeError):
            continue
    return {"game": game, "candidates": results, "warnings": warnings,
            "selection": "Confirm exact active profiles in-game; candidate files are not proof of active selection."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("discover", "inventory"):
        child = sub.add_parser(name)
        child.add_argument("--game", choices=GAMES, required=True)
        child.add_argument("--output", type=Path)
        if name == "discover":
            child.add_argument("--root", type=Path, required=True)
        else:
            child.add_argument("--profile", type=Path, action="append", required=True)
            child.add_argument("--device-map", type=Path)
            child.add_argument("--require-action", action="append", default=[])
            child.add_argument("--active-confirmed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "discover":
            report = discover(args.game, args.root)
        else:
            devices = json.loads(args.device_map.read_text(encoding="utf-8-sig")) if args.device_map else {}
            report = inventory(args.game, args.profile, devices, args.require_action, args.active_confirmed)
        text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
        else:
            print(text, end="")
        return 0
    except (OSError, ValueError, ET.ParseError, UnicodeError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
