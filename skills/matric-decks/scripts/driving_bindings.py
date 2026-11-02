"""Read-only driving/farming input formats; no game or driver access."""
import json
import re
import struct
import uuid
import xml.etree.ElementTree as ET

from deck_tool import action


def plausible_driving(game, path):
    """Limit candidate discovery to input configuration filenames."""
    name = path.name.lower()
    return (name == "controls.sii" if game == "ets2" else
            name == "inputbinding.xml" if game == "farmingsimulator" else
            name == "controls.cfg" if game == "iracing" else
            path.suffix.lower() == ".json")


def parse_driving(game, data, row):
    """Return common inventory rows with the original configuration retained."""
    metadata = {"warnings": [], "format": game}
    rows = []
    if game == "ets2":
        if not data.lstrip().startswith("SiiNunit"):
            raise ValueError("Expected readable SCS SiiNunit controls; encrypted/binary files unsupported")
        metadata["raw"] = data
        for match in re.finditer(r'config_lines\[(\d+)\]\s*:\s*("(?:\\.|[^"\\])*")', data):
            line = json.loads(match[2])
            mix = re.fullmatch(r'mix\s+(\S+)\s+`(.*)`', line)
            if not mix:
                continue
            name, expression = mix.groups()
            simple = re.fullmatch(r'keyboard\.([a-z0-9_]+)\?0', expression)
            rows.append(row("profile", name, match[1], "Keyboard" if simple else "scs-expression",
                            [simple[1] if simple else expression], settings={"raw": line,
                            "expression": expression, "manual_only": not bool(simple)},
                            unbound=expression.strip() == "0"))
        metadata["warnings"].append("Mix expressions, aliases, constants and timing are retained, not evaluated. Only single keyboard inputs translate automatically; confirm ETS2 edition/build and selected local or Steam profile.")
    elif game == "farmingsimulator":
        if data.tag != "inputBinding":
            raise ValueError("Expected GIANTS inputBinding XML")
        metadata["attributes"] = dict(data.attrib)
        metadata["xml"] = ET.tostring(data, encoding="unicode")
        for group in data.iter("actionBinding"):
            for index, binding in enumerate(group.findall("binding")):
                tokens = binding.get("input", "").split()
                rows.append(row("profile", group.get("action", ""), binding.get("index", str(index)),
                                binding.get("device", ""), tokens,
                                settings={"binding": dict(binding.attrib), "action": dict(group.attrib)},
                                unbound=not tokens))
        metadata["warnings"].append("Confirm Farming Simulator edition, active inputBinding.xml, mods and device identities. Axis/input components, neutral values and indices are retained; no numeric device or axis conversion is inferred.")
    elif game == "acc":
        document = json.loads(data)
        if not isinstance(document, dict) or not any(k in document for k in ("keyboardSettings", "raceCommandButtonList", "commandDevices", "wheelSettings", "gamepadSettings")):
            raise ValueError("Expected ACC input configuration JSON")
        metadata["document"] = document

        def visit(node, context="profile", device="acc-unresolved"):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ("raceCommandButtonList", "uICommandButtonList") and isinstance(value, list):
                        for index, entry in enumerate(value):
                            if not isinstance(entry, dict):
                                raise ValueError("ACC command entry must be an object")
                            chord = entry.get("key", {})
                            chord_known = isinstance(chord, dict) and isinstance(chord.get("key"), str)
                            if not isinstance(chord, dict):
                                chord = {}
                            token = chord.get("key", entry.get("keyName", "unresolved"))
                            for field in ("actionType", "instantActionCode", "extendedActionCode", "pinkieInstanceActionCode", "pinkieExtendedActionCode"):
                                command = entry.get(field)
                                if not command or command == "None":
                                    continue
                                if not isinstance(command, str):
                                    raise ValueError("ACC action identifier must be a string")
                                mods = [{"device": "Keyboard", "key": m} for flag, m in
                                        (("bShift", "lshift"), ("bCtrl", "lctrl"), ("bAlt", "lalt"), ("bCmd", "cmd")) if chord.get(flag)]
                                keyboard = device == "Keyboard"
                                inputs = [str(token)] if keyboard else [json.dumps({k: entry.get(k) for k in ("buttonIndex", "powIndex", "powValue", "keyName", "gamepadButtonName")}, sort_keys=True)]
                                rows.append(row(context + "/" + key, command, str(index) + ":" + field,
                                                device, inputs, mods, {"entry": entry,
                                                "manual_only": not keyboard or field != "actionType" or not chord_known
                                                or any(type(chord[f]) is not bool for f in ("bShift", "bCtrl", "bAlt", "bCmd") if f in chord)},
                                                keyboard and chord_known and token in ("None", "")))
                    else:
                        visit(value, context + "/" + key, "Keyboard" if key == "keyboardSettings" else device)
            elif isinstance(node, list):
                for index, child in enumerate(node):
                    visit(child, context + "/" + str(index), device + ":" + str(index))
        visit(document)
        metadata["warnings"].append("ACC raw JSON retains axis/device configuration and extensions. Wheel/gamepad inputs, long presses and pinkie actions require review; no controller identity, precedence or timing is inferred. Confirm the active preset in-game.")
    else:
        if len(data) < 12 or data[:4] != b"GFCC":
            raise ValueError("Expected iRacing GFCC controls.cfg")
        version, size = struct.unpack_from("<II", data, 4)
        if size != len(data) - 12:
            raise ValueError("Invalid GFCC payload size")
        offset = data.find(b"LRTC", 12)
        if offset < 0 or offset + 12 > len(data):
            raise ValueError("Missing/truncated iRacing LRTC header")
        lver, length = struct.unpack_from("<II", data, offset + 4)
        if (version, lver) != (20, 8):
            raise ValueError("Unsupported iRacing GFCC/LRTC versions; verified subset is 20/8")
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("Truncated LRTC payload")
        metadata.update({"version": version, "controls_version": lver,
                         "global_hex": data[12:offset].hex(), "trailer_hex": data[end:].hex()})
        position = offset + 12
        while position < end:
            zero = data.find(b"\0", position, end)
            if zero < 0 or zero + 69 > end:
                raise ValueError("Truncated iRacing control record")
            name = data[position:zero].decode("ascii")
            body = data[zero+1:zero+69]
            unknown, flags, kind, value, modifiers = struct.unpack_from("<5I", body)
            slots = [str(uuid.UUID(bytes_le=body[i:i+16])) for i in (20, 36, 52)]
            rows.append(row("profile", name, str(len(rows)), "iracing:" + ":".join(slots),
                            [str(kind) + ":" + str(value)], settings={"type": kind, "value": value,
                            "modifiers": modifiers, "flags": flags, "unknown": unknown,
                            "slots": slots, "raw_hex": body.hex(), "manual_only": True}, unbound=kind == 0))
            position = zero + 69
        metadata["warnings"].append("Experimental reverse-engineered GFCC/LRTC record inventory. All input translations remain manual, including key codes/modifiers and device slots. Global/car-specific selection and built-in defaults require in-game confirmation; calibration is separate in joyCalib.yaml.")
    return metadata, rows


def keyboard_action(binding, key_code):
    """Translate only simple verified keyboard tokens, retaining other semantics."""
    if binding["device"] not in ("Keyboard", "KB_MOUSE_DEFAULT"):
        return None
    tokens = binding["inputs"]
    if not tokens:
        return None
    codes = [key_code({"SpaceBar": "space"}.get(t, t)) for t in tokens]
    codes += [key_code(m["key"]) for m in binding["modifiers"]]
    if any(c is None for c in codes):
        return None
    modifiers = {160: "LSHIFT", 161: "RSHIFT", 162: "LCONTROL", 163: "RCONTROL", 164: "LALT", 165: "RALTGRAPH"}
    main = [c for c in codes if c not in modifiers]
    if len(main) != 1:
        return None
    return action("ActionHotkey", KeyCode=main[0], Keystroke=str(main[0]),
                  Modifiers=list(dict.fromkeys(modifiers[c] for c in codes if c in modifiers)), Toggle=False)
