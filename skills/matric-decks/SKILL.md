---
name: matric-decks
license: MIT
description: Create, inspect, or edit MATRIC control decks and produce importable .deck packages without using the editor. Use for MATRIC layouts, action bindings, resources, custom applets, OBS, DCS-BIOS/DBMM, and MSFS, Star Citizen or Elite Dangerous input panels.
---

# MATRIC deck authoring

Produce an editable MATRIC deck, its assets, and an importable `.deck` file. Work in a staging folder; MATRIC and its editor are not required for generation. The bundled Python helpers use only the standard library.

## Establish the working context

Use the user's requested application, controls, target screen/orientation, and supplied shortcut mappings. Infer routine design choices; ask when missing information changes what actions can actually work. Do not invent application shortcuts, OBS source names, device IDs, or plugin settings. A clearly labelled layout-only control is preferable to a fabricated binding when the user accepts an unfinished layout.

When useful and internet access is available, look for an existing deck in the [MATRIC Community gallery](https://community.matricapp.com/) that could match the request. Suggest a relevant result with a direct link, explain what matches and any known gaps or dependencies, and distinguish unverified behavior from confirmed details. Continue the requested authoring work unless the user chooses the existing deck instead. Do not assume a gallery deck's assets or configuration can be redistributed or reused without checking its terms.

Treat the intended client screen as usability input before choosing layout density: use the device model or physical screen size, resolution/aspect ratio and orientation when available. If the target is unknown and it affects whether the controls will be usable, ask whether the user will use a phone or tablet and its approximate size. A dense panel that works on a 9-inch tablet may fit but be impractical to touch on a phone; resolution alone does not establish physical target size. Adapt control sizes, spacing, labels and page count accordingly; see [target screens and touch usability](references/deck-format.md#target-screens-and-touch-usability).

Write the deck description for the person importing it, not for an implementer: plainly say what the deck is for and its intended device size, aspect ratio, and orientation (or clearly label an assumption). Keep control types, grid mechanics, binding names and other implementation detail out of that description. If it refers to a companion setup guide, include the stable URL to that guide; do not say merely "see the guide" or invent a URL. Keep technical setup detail in the guide or delivery notes. See [deck descriptions and companion guides](references/deck-format.md#deck-descriptions-and-companion-guides).

Read [the deck format](references/deck-format.md) before authoring. The important distinction is that `.deck` is a ZIP containing `<deck-id>/deck2.json` and resources under that same folder. Renaming a bare JSON file or placing JSON at the archive root does not create an importable package.

For a new panel, choose the grid and controls to suit the task. For an existing deck, unpack a copy and preserve unrelated controls, metadata, assets, identities, and opaque settings. Keep its deck ID for an intended update; importing that ID replaces that installed deck. A separate new deck needs fresh deck/page/control IDs and remapped navigation. Plugin-owned resource identities need MATRIC's own copy/export handling.

Keep every page within MATRIC's supported limit: integer `Cols` and `Rows` from 1 through 50, independently. Larger pages may render but are unsupported and can cause stability/performance issues; do not treat rendering or an older validator's acceptance as permission to exceed 50×50. If the requested grouping cannot fit after compact sizing, resolve the scope/layout constraint with the user rather than silently enlarging the page beyond that limit.

## Use actual MATRIC definitions

Run the helper relative to this skill directory; replace `python` with the environment's available Python 3 executable:

```text
python scripts/deck_tool.py catalog
python scripts/deck_tool.py catalog --control MCButton
python scripts/deck_tool.py catalog --action ActionHotkey
```

The catalog was exported from MATRIC's C# definitions, not inferred from screenshots. Inspect the entries needed for this task instead of loading the entire catalog. They provide exact type names, defaults, event names, allowed actions, enum encodings, and key codes. Use [action recipes](references/action-recipes.md) for semantic details the catalog cannot infer.

Prefer a native control that matches the interaction: a multi-position switch for a discrete selector, a rotary encoder for relative turning, and a rotary/slider for absolute input. Direct-selection buttons are appropriate when named choices or frequently used presets are easier to reach on the target screen; bind each choice to a verified command and, when available, actual-state feedback. Skin the native control with its own resources and verify its events and simulator/app feedback mapping; see [native selectors and rotary controls](references/action-recipes.md#native-selectors-and-rotary-controls).

When native controls cannot satisfactorily express a requested interaction or visualization, use the advanced [custom applet workflow](references/custom-applets.md). It covers original HTML/CSS/JavaScript applets, manifests, variables/events, responsive input handling, manifest-aware deck checks and separate `.mapl` packaging. Prefer native controls for ordinary buttons/sliders/rotaries, including when only their appearance needs changing. Do not install an applet into the live library to test generation.

Every applet authored must expose configurable `Padding` (nonnegative iframe CSS pixels) and `BackgroundColor` (a color parameter), with matching runtime defaults. Apply the padding inside the iframe edge, outside any proportional design scaling, and paint the entire iframe with the selected background color. Preserve these settings on partial parameter updates. See the applet reference for fitting and validation details.

## Reuse installed visual templates first

Before creating new button or control artwork, inspect the user's installed MATRIC template decks when their deck library is available. For ordinary decks, begin with **Default control templates**. For DCS decks, inspect **Aviation button templates** first for its aviation-inspired skeuomorphic controls, then Default control templates. Identify them by deck title rather than a fixed folder ID. They are normally pre-installed, but a user may have removed them; their absence must never block authoring, validation, or packaging.

When a suitable template exists, create a fresh target control from the catalog and transfer only its visual configuration and every resource required by its normal and active states. Do not inherit the template's actions, bindings, control ID, variables, or unrelated behavior; author the target interaction separately. Do not bundle or redistribute template-deck assets in this skill. For the detailed resource workflow and fallback rules, read [reusing installed control templates](references/deck-format.md#reusing-installed-control-templates).

Create a blank staged deck with:

```text
python scripts/deck_tool.py new --title "My panel" --cols 6 --rows 4 --output /path/to/staged-deck
```

Edit its `deck2.json`. In a Python authoring script, import `new_control` and `action` from `scripts/deck_tool.py` to clone runtime defaults with fresh control IDs and a readable appearance. The helpers build data; they do not execute actions. See `assets/starter/deck2.json` for a complete native example with navigation, hotkeys, text, and a bundled SVG background. Generate fresh IDs when adapting it into a new deck.

**All deck assets MUST be in the same folder as `deck2.json`. No subfolders are allowed: nested assets do not work correctly in MATRIC.** Reference images, audio and other deck resources by filename only, such as `button-off.png`, never `images/button-off.png`. When flattening an existing deck, resolve filename collisions explicitly and update every affected reference, including normal/active states and resource lists; do not overwrite assets silently. This rule concerns deck resources, not the internal layout of separately packaged applets.

Prefer native colors/text/icons for simple panels; create original images when no suitable installed template exists or the user has requested a specific visual design. Grid dimensions and positions are cell counts, not pixels. In the inspected native renderer, TextSize is a percentage of the control's shorter dimension: `cellSize * min(Height, Width) * TextSize / 100`, not a font size in points. Recheck labels when changing control spans.

Keep controls self-contained as a general authoring rule, especially for inventories/templates users drag into other layouts. Put each control's identifying label, artwork, actions and feedback on that control, not on neighboring label widgets or page artwork. If an operation needs multiple controls, make each independently understandable and functional when copied, and disclose any shared variables or separately installed applet dependencies. Copy referenced resources with the control; do not infer that a visually complete group will be copied together.

Use the smallest practical row/column spans for each control, preserving necessary labels, state information and interaction. Especially in draggable inventories, avoid inflated footprints and empty decorative padding: a user can enlarge a compact source control, but cannot drop a 15×15 control onto a 10×10 deck. Size simple warning/caution indicators as compact indicators, not large cards by default. A large page budget is not a reason to enlarge its controls. Recheck text/artwork at the smaller spans; retain usable touch areas when authoring an operational layout.

Fonts are intentionally not packaged with decks, to avoid unlicensed redistribution of copyrighted fonts. Do not bundle font files or assume a specific system/custom font is available. Use MATRIC's default text font unless a font is important to reproducing a requested visual style, such as a seven-segment display. Recommend or use a non-standard font only from DaFont or Google Fonts, name it and give its permitted download link in the deck description, and explain that it must be installed separately in MATRIC's fonts folder. If its value is unclear, explain this plainly and ask whether the user agrees before using it. See [fonts and optional fidelity](references/deck-format.md#fonts-and-optional-fidelity).

Design for client scaling, not pixel-perfect composition. MATRIC adapts the page to the client's screen proportions; page backgrounds and controls do not share a guaranteed pixel coordinate system. Avoid painting labels, bezels, display cutouts or knob faces into a page background and positioning separate controls over them. Keep those visuals on the controls themselves (for example, button backgrounds or rotary dial images); use page backgrounds for plain color or non-alignment-dependent decoration. Matching Cols/Rows to a target screen does not guarantee exact registration. See [client scaling and backgrounds](references/deck-format.md#client-scaling-and-backgrounds).

Before delivering a new or revised illustrated deck, hide its page background and check that each control still has its complete label, bezel and state display. Move any missing alignment-dependent artwork onto that control; merely documenting the limitation does not fix it. Do not assume a fixed-proportion rendering mode exists in the target client.

## HTTP-backed controls and dashboards

For HTTP-backed controls and dashboards, read [HTTP requests and calculated parameters](references/action-recipes.md#http-requests-and-calculated-parameters). Newer MATRIC builds can calculate request URLs, methods, headers and bodies from server variables and event data, execute the request on the PC, and publish response variables for native controls or applets. Check this native path before proposing browser fetch or a separate companion service; verify endpoint authentication and target-build support.

## OBS panels

When the task involves OBS collections, scenes, sources, groups, filters, transitions, or shortcuts, read [OBS discovery](references/obs-discovery.md). Prefer a live, read-only snapshot when OBS is running and its WebSocket endpoint is available. The bundled standard-library client authenticates through an environment variable or a private interactive prompt; keep credentials outside chat prompts, reports and deck files. Use saved collection files for offline discovery, inactive collections or saved keyboard bindings:

```text
python scripts/obs_live.py --url ws://127.0.0.1:4455 --output /path/to/obs-live.json
python scripts/obs_inventory.py /path/to/collection.json
python scripts/obs_inventory.py /path/to/basic/scenes --output /path/to/obs-inventory.json
```

Use the exact discovered names when configuring native OBS actions. Review snapshot warnings and scope before using the results: live discovery describes the active collection and default canvas at discovery time; hotkey identifiers are not keyboard bindings. Saved files describe saved configuration. Do not switch collections or start/stop outputs just to discover a setup. No MATRIC connection is required for discovery; native MATRIC OBS actions still need MATRIC's OBS integration to execute.

## DCS cockpit panels

For Digital Combat Simulator decks with two-way DCS-BIOS-MATRIC-Middleware (DBMM) integration, read [the DCS workflow](references/dcs-bios.md). Inspect the user's installed aircraft JSON and aliases with `scripts/dcs_bios.py inventory`; use `check` to audit commands and feedback dependencies. Do not guess aircraft identifiers, switch semantics, seat variants or live values. DBMM sends commands through `DCS_INPUT_COMMAND` and publishes telemetry as `dcs_<identifier>`. Initialize the command mailbox empty; keep simulator state separate from persistent user variables. The deck description must state that DBMM with DCS-BIOS is required and include the prescribed DBMM and DCS-BIOS release URLs.

The DCS reference covers setup, momentary commands, switch/slider mapping, feedback transforms, required exported variables and live acceptance. `scripts/dcs_bios.py example --output /path/to/dcs-training` produces a synthetic training deck, not a real aircraft panel. Existing DBMM decks are evidence to inspect; preserve their assets and do not copy stale commands or unknown mappings into new work. Keep aircraft definitions and real user decks outside the distributed skill.

Use [cockpit layout and reference-deck lessons](references/dcs-bios.md#cockpit-layout-and-reference-decks) when adapting an existing panel or learning from a user example. Prioritize touch usability and the user's workflow; cockpit appearance/layout is an optional design choice, not the default measure of quality. A tablet lacks physical controls' tactile cues and is often much smaller than the cockpit panel. Group frequently used functions together even when scattered around the real cockpit, especially for vintage aircraft with limited HOTAS. On layout-only revisions, compare commands, event assignments and feedback dependencies with the baseline rather than treating structural validation as proof that behavior was preserved.

## Flight and space simulator inputs

For Microsoft Flight Simulator 2020/2024, Star Citizen or Elite Dangerous, read [game input discovery and authoring](references/game-inputs.md). Use `scripts/game_bindings.py discover` within the relevant game/settings folder, then `inventory` on explicitly selected active profile files. Preserve action/context identifiers, alternatives, modifiers, activation timing and axis settings. Star Citizen explicit exports may omit defaults; MSFS profile layers require confirmation. Unknown mappings must stay unresolved rather than inheriting remembered defaults.

Use native keyboard and vJoy actions as appropriate. Confirm the actual game-to-vJoy device correspondence and configured capabilities before translating joystick buttons/axes/POVs; physical-device mappings do not establish that correspondence. Focus suggested layouts on auxiliary controls such as throttle, flaps, mixture, radiators, lights and ship systems; omit primary flight-stick controls unless requested. These integrations provide input only, with local control positions distinct from actual game state. Deliver setup/rebinding requirements and distinguish offline validation from acceptance in the user's game.

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

If a static preview would help, create one and identify it as an approximation, not proof of background/control alignment on a client. Review illustrated layouts at the target proportions and a differing aspect ratio when rendering is available; distinguish an offline layout model from an actual MATRIC-client capture. A rendered MATRIC-client preview is stronger evidence when the actual client renderer is available. Do not make editor operation or a preview tool unavailable on another machine a prerequisite for producing the package.

Deliver the `.deck` package and editable source/assets, with brief import and setup instructions. Identify unresolved bindings and external dependencies. Import through MATRIC's existing deck-import workflow; installing a skill does not install the generated deck. Do not place files directly in a live library or activate controls merely to test generation.

## Compatibility

The bundled catalog records its deck format version, source commit and assembly hash in `references/catalog.json`. For a newer MATRIC target, refresh the catalog from that build before claiming support for new fields/types. The repository maintainer can run `tools/refresh-matric-catalog.ps1 -DesktopBin <built-desktop-folder> -MatricSourceCommit <MATRIC-source-commit>` in the separate `matric-deck-skill` repository; that developer-only refresh tool is outside the distributable skill.

Stream Deck plugin support remains experimental. Preserve existing opaque configurations when applicable, and use known tested examples for new bindings. DRM-protected plugins, Elgato action/profile import/export, profile switching/deep links, continuous slider mappings and touch-strip support are outside the supported Stream Deck scope. Plugin packages, credentials, custom applets, custom fonts, and machine-specific applications are not automatically made portable by a `.deck` archive.
