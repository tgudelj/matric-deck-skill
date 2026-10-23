#!/usr/bin/env python3
"""Read OBS scene collections without MATRIC, a network connection or changes to OBS files."""
import argparse
import json
import sys
from pathlib import Path


def hotkeys(value):
    """Extract shortcut keys and modifier flags without copying unrelated source settings."""
    if not isinstance(value, dict):
        return {}
    fields = ("key", "shift", "control", "alt", "command")
    return {name: [{k: binding[k] for k in fields if k in binding} for binding in bindings if isinstance(binding, dict)]
            for name, bindings in value.items() if isinstance(bindings, list)}


def inventory(path):
    """Describe saved scenes, groups, inputs, filters, global audio and their membership by exact name/UUID."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise ValueError(f"{Path(path).name} does not contain an OBS scene collection sources array")
    sources = [v for key in ("sources", "groups") for v in data.get(key, []) if isinstance(v, dict)]
    # OBS stores globally configured audio devices alongside the main sources array.
    sources.extend(v for k, v in data.items() if (k.startswith("AuxAudioDevice") or k.startswith("DesktopAudioDevice")) and isinstance(v, dict))
    unique = {}
    for source in sources:
        if isinstance(source.get("name"), str):
            unique[source.get("uuid") or source["name"]] = source
    sources = list(unique.values())
    by_uuid = {v["uuid"]: v for v in sources if v.get("uuid")}
    by_name = {v["name"]: v for v in sources}
    warnings = []
    def kind(source):
        return source.get("id") or source.get("versioned_id")
    def summary(source):
        result = {"name": source["name"], "uuid": source.get("uuid"), "kind": kind(source),
                  "filters": [{"name": f.get("name"), "kind": kind(f)} for f in source.get("filters", []) if isinstance(f, dict)],
                  "hotkeys": hotkeys(source.get("hotkeys"))}
        for key in ("volume", "muted", "enabled"):
            if type(source.get(key)) in (bool, int, float):
                result["saved_" + key] = source[key]
        return result
    containers = []
    for source in sources:
        if kind(source) not in ("scene", "group"):
            continue
        container = {"name": source["name"], "uuid": source.get("uuid"), "kind": kind(source), "items": []}
        settings = source.get("settings") or {}
        for item in settings.get("items", []):
            if not isinstance(item, dict):
                continue
            linked = by_uuid.get(item.get("source_uuid")) or by_name.get(item.get("name"))
            name = linked["name"] if linked else item.get("name")
            if linked is None:
                warnings.append(f"{source['name']}: unresolved item {name!r}")
            container["items"].append({"name": name, "source_uuid": item.get("source_uuid"), "item_id": item.get("id"),
                                       "kind": kind(linked) if linked else None, "saved_visible": item.get("visible"), "saved_locked": item.get("locked")})
        containers.append(container)
    order = [v["name"] for v in data.get("scene_order", []) if isinstance(v, dict) and isinstance(v.get("name"), str)]
    return {"collection": data.get("name") or Path(path).stem, "origin": "saved_scene_collection", "live": False,
            "saved_current_scene": data.get("current_scene"), "saved_program_scene": data.get("current_program_scene"),
            "scene_order": order, "containers": containers, "sources": [summary(v) for v in sources],
            "transitions": [{"name": t.get("name"), "kind": kind(t)} for t in data.get("transitions", []) if isinstance(t, dict)],
            "hotkeys": hotkeys(data.get("hotkeys")), "warnings": warnings}


def main():
    """Inspect one JSON file or all scene-collection JSON files in an explicitly supplied directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = sorted(args.source.glob("*.json")) if args.source.is_dir() else [args.source]
    if not paths:
        parser.error("No scene collection JSON files found")
    result = {"collections": [inventory(path) for path in paths]}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
