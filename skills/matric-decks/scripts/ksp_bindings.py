"""Inventory KSP 1 ConfigNode input settings without changing or executing them."""
import re

from deck_tool import action


def parse_ksp(text, row):
    """Read line-based ConfigNode syntax, preserving duplicates and nested fields."""
    root = {"name": "", "values": [], "children": []}
    stack = [root]
    pending = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = re.sub(r"\s+//.*$", "", raw).strip()
        if not line or line.startswith("//"):
            continue
        if line.endswith("{") and line != "{":
            if pending is not None:
                raise ValueError("Missing KSP node opening brace")
            pending = line[:-1].strip()
            line = "{"
        if line == "{":
            if not pending or len(stack) >= 64:
                raise ValueError("Invalid or excessively nested KSP node")
            child = {"name": pending, "values": [], "children": [], "line": number}
            stack[-1]["children"].append(child)
            stack.append(child)
            pending = None
        elif line == "}":
            if pending is not None or len(stack) == 1:
                raise ValueError("Unmatched KSP closing brace")
            stack.pop()
        elif "=" in line:
            if pending is not None:
                raise ValueError("Missing KSP node opening brace")
            key, value = line.split("=", 1)
            stack[-1]["values"].append([key.strip(), value.strip()])
        else:
            if pending is not None or any(c in line for c in "{}"):
                raise ValueError("Unsupported KSP ConfigNode syntax at line " + str(number))
            pending = line
    if pending is not None or len(stack) != 1:
        raise ValueError("Incomplete KSP ConfigNode")
    rows = []
    for node in root["children"]:
        fields = dict(node["values"])
        name = node["name"]
        axis = name.lower().startswith("axis_")
        if axis:
            alternatives = node["children"] or [node]
            for index, slot in enumerate(alternatives):
                values = dict(slot["values"])
                if "axis" not in values and "id" not in values:
                    continue
                device = values.get("name", "unresolved")
                token = "axis:" + values["axis"] if "axis" in values else "id:" + values["id"]
                rows.append(row("profile", name, slot["name"] + ":" + str(index), device,
                                [token], settings={"node": node, "axis": values,
                                "manual_only": "axis" not in values},
                                unbound=device == "None" or values.get("axis") == "-1" or values.get("id") == "None"))
        elif "primary" in fields or "secondary" in fields:
            for index, (slot, token) in enumerate(node["values"]):
                if slot not in ("primary", "secondary"):
                    continue
                joystick = re.fullmatch(r"Joystick(\d*)Button\d+", token)
                device = "Joystick" + (joystick[1] or "Any") if joystick else "Keyboard"
                rows.append(row("profile", name, slot + ":" + str(index), device, [token],
                                settings={"node": node, "manual_only": fields.get("switchState", "Any") != "Any"},
                                unbound=token == "None"))
    if not rows:
        raise ValueError("No supported KSP 1 input binding nodes")
    return {"format": "ksp1", "configuration": root, "raw": text, "warnings": [
        "KSP 1 saved settings only. Confirm installation, input groups, switchState and axis modeMask in-game. Unknown keys and modifier-only bindings remain unresolved; no implicit MODIFIER_KEY chord or joystick identity is inferred. Mods and KSP 2 use separate configurations."]}, rows


def keyboard_action(binding, key_code):
    """Translate a known Unity key name, never its numeric enum value."""
    if binding["device"] != "Keyboard":
        return None
    token = binding["inputs"][0]
    if re.fullmatch(r"Alpha[0-9]", token):
        token = token[-1]
    if re.fullmatch(r"Keypad[0-9]", token):
        token = "numpad" + token[-1]
    code = key_code(token)
    if code is None or code in (160, 161, 162, 163, 164, 165):
        return None
    return action("ActionHotkey", KeyCode=code, Keystroke=str(code), Modifiers=[], Toggle=False)
