---
name: matric-decks
license: MIT
description: Create, inspect, or edit MATRIC control decks and produce importable .deck packages without using the editor. Use for MATRIC deck JSON, layouts, action bindings, resources, and OBS or DCS-BIOS/DBMM control panels.
---

# MATRIC deck authoring

Produce an editable MATRIC deck, its assets, and an importable `.deck` file. Work in a staging folder; MATRIC and its editor are not required for generation. The bundled Python helpers use only the standard library.

## Establish the working context

Use the user's requested application, controls, target screen/orientation, and supplied shortcut mappings. Infer routine design choices; ask when missing information changes what actions can actually work. Do not invent application shortcuts, OBS source names, device IDs, or plugin settings. A clearly labelled layout-only control is preferable to a fabricated binding when the user accepts an unfinished layout.

Read [the deck format](references/deck-format.md) before authoring. The important distinction is that `.deck` is a ZIP containing `<deck-id>/deck2.json` and resources under that same folder. Renaming a bare JSON file or placing JSON at the archive root does not create an importable package.

For a new panel, choose the grid and controls to suit the task. For an existing deck, unpack a copy and preserve unrelated controls, metadata, assets, identities, and opaque settings. Keep its deck ID for an intended update; importing that ID replaces that installed deck. A separate new deck needs fresh deck/page/control IDs and remapped navigation. Plugin-owned resource identities need MATRIC's own copy/export handling.

## Use actual MATRIC definitions

Run the helper relative to this skill directory; replace `python` with the environment's available Python 3 executable:

```text
python scripts/deck_tool.py catalog
python scripts/deck_tool.py catalog --control MCButton
python scripts/deck_tool.py catalog --action ActionHotkey
```

The catalog was exported from MATRIC's C# definitions, not inferred from screenshots. Inspect the entries needed for this task instead of loading the entire catalog. They provide exact type names, defaults, event names, allowed actions, enum encodings, and key codes. Use [action recipes](references/action-recipes.md) for semantic details the catalog cannot infer.

Create a blank staged deck with:

```text
python scripts/deck_tool.py new --title "My panel" --cols 6 --rows 4 --output /path/to/staged-deck
```

Edit its `deck2.json`. In a Python authoring script, import `new_control` and `action` from `scripts/deck_tool.py` to clone runtime defaults with fresh control IDs and a readable appearance. The helpers build data; they do not execute actions. See `assets/starter/deck2.json` for a complete native example with navigation, hotkeys, text, and a bundled SVG background. Generate fresh IDs when adapting it into a new deck.

Place file resources in the staged folder, and reference them relative to that folder. Prefer native colors/text/icons for simple panels; create images when they improve the requested design. Grid dimensions and positions are cell counts, not pixels. TextSize is a percentage of one grid cell, not a font size in points.

## OBS panels

When the task involves OBS collections, scenes, sources, groups, filters, transitions, or shortcuts, read [OBS discovery](references/obs-discovery.md). The skill can inspect saved OBS scene-collection files independently of MATRIC:

```text
python scripts/obs_inventory.py /path/to/collection.json
python scripts/obs_inventory.py /path/to/basic/scenes --output /path/to/obs-inventory.json
```

Use the exact discovered names when configuring native OBS actions. The helper's result is saved configuration, not live state. The OBS reference also describes direct, read-only obs-websocket 5 discovery for assistants with a WebSocket client. Do not switch collections or start/stop outputs just to discover a setup. No MATRIC MCP server or MATRIC-as-WebSocket-client is required for discovery.

## DCS cockpit panels

For Digital Combat Simulator decks with two-way DCS-BIOS-MATRIC-Middleware (DBMM) integration, read [the DCS workflow](references/dcs-bios.md). Inspect the user's installed aircraft JSON and aliases with `scripts/dcs_bios.py inventory`; use `check` to audit commands and feedback dependencies. Do not guess aircraft identifiers, switch semantics, seat variants or live values. DBMM sends commands through `DCS_INPUT_COMMAND` and publishes telemetry as `dcs_<identifier>`. Initialize the command mailbox empty; keep simulator state separate from persistent user variables.

The DCS reference covers setup, momentary commands, switch/slider mapping, feedback transforms, required exported variables and live acceptance. `scripts/dcs_bios.py example --output /path/to/dcs-training` produces a synthetic training deck, not a real aircraft panel. Existing DBMM decks are evidence to inspect; preserve their assets and do not copy stale commands or unknown mappings into new work. Keep aircraft definitions and real user decks outside the distributed skill.

## Validate and package

```text
python scripts/deck_tool.py validate /path/to/staged-deck
python scripts/deck_tool.py pack /path/to/staged-deck --output /path/to/MyPanel.deck
python scripts/deck_tool.py validate /path/to/MyPanel.deck
```

Resolve errors. Review warnings such as intentional overlaps and separately installed dependencies. Validation checks structure, known field types/enums, control/event/action compatibility, bounds, IDs, navigation, and native image/audio resources. It cannot prove a shortcut's meaning, a target app's availability, live OBS state, opaque plugin settings, or the appearance on every device. Do not describe static validation as an end-to-end application test.

The packager refuses to overwrite an existing archive. Use a new filename for a revision. To edit an exported deck:

```text
python scripts/deck_tool.py unpack /path/to/Input.deck --output /path/to/working-copy
```

If a static preview would help, create one and identify it as an approximation. A rendered MATRIC-client preview is stronger evidence when the actual client renderer is available. Do not make editor operation or a preview tool unavailable on another machine a prerequisite for producing the package.

Deliver the `.deck` package and editable source/assets, with brief import and setup instructions. Identify unresolved bindings and external dependencies. Import through MATRIC's existing deck-import workflow; installing a skill does not install the generated deck. Do not place files directly in a live library or activate controls merely to test generation.

## Compatibility

The bundled catalog records its deck format version, source commit and assembly hash in `references/catalog.json`. For a newer MATRIC target, refresh the catalog from that build before claiming support for new fields/types. The repository maintainer can run `tools/refresh-matric-catalog.ps1 -DesktopBin <built-desktop-folder> -MatricSourceCommit <MATRIC-source-commit>` in the separate `matric-deck-skill` repository; that developer-only refresh tool is outside the distributable skill.

Stream Deck plugin support remains experimental. Preserve existing opaque configurations when applicable, and use known tested examples for new bindings. DRM-protected plugins, Elgato action/profile import/export, profile switching/deep links, continuous slider mappings and touch-strip support are outside the supported Stream Deck scope. Plugin packages, credentials, custom applets, custom fonts, and machine-specific applications are not automatically made portable by a `.deck` archive.
