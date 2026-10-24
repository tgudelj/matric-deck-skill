# Development and compatibility

## Current state

Current release: 0.2.0. Initial version 0.1.0 was extracted into a separate project on 2026-10-23. The installed skill includes instructions, deck/action/OBS references, a catalog of actual MATRIC definitions, standard-library Python helpers, and a two-page starter deck with an SVG background. Runtime authoring and ordinary testing are independent of the MATRIC source tree.

The original acceptance run passed eight offline tests and MATRIC's native import â†’ export â†’ reimport check, preserving two pages, five controls, hotkey configuration and the bundled SVG. OBS discovery was also exercised against a local saved collection; that user configuration is not part of this repository. Repository extraction adds a packaging acceptance test and cross-platform CI configuration. Local standalone validation passed all nine tests, release packaging/checksum verification, native import/export/reimport, and catalog refresh against the identified MATRIC build. GitHub CI passed on Windows and Linux for the initial push and release tag: [main run](https://github.com/tgudelj/matric-deck-skill/actions/runs/40028705824), [v0.1.0 run](https://github.com/tgudelj/matric-deck-skill/actions/runs/40028707247).

The public [v0.1.0 release](https://github.com/tgudelj/matric-deck-skill/releases/tag/v0.1.0) is published under MIT. Its downloaded ZIP and SHA-256 were verified, and installation from the tagged GitHub skill directory was checked against the release source. The active local skill installation was updated from that version. The previous skill additions and manual edits were removed from the MATRIC working tree, leaving it clean.

Saved OBS discovery is implemented. Direct read-only obs-websocket discovery is described in the guide; a live client is not implemented. A rendered MATRIC-client preview is also not implemented. Preserve this distinction in user-facing claims.

## Installation documentation

`docs/INSTALLATION.md` covers Codex, Claude Code, Cursor, GitHub Copilot and Gemini CLI, with vendor-source links, personal/project locations, invocation, Python verification, cloud/remote constraints and updates. Copilot's optional `gh skill` flow is marked as preview and version-dependent; Cursor uses manual folder installation because this repository has no plugin marketplace manifest. Installation guidance was checked against vendor documentation; other harnesses have not been tested end to end. The installed payload remains v0.1.0; these are repository documentation changes only.

## DCS extension in version 0.2.0

The existing skill now routes DCS cockpit tasks to `references/dcs-bios.md` and `scripts/dcs_bios.py`. The helper reads installed DCS-BIOS JSON/aircraft aliases, validates literal command arguments, generates command-variable actions and feedback bindings, audits mailbox/dependencies, and creates an original synthetic training deck. No aircraft definition dataset, real user deck or third-party artwork is bundled. All work remains separate from the MATRIC application repository.

Evidence includes the public DBMM translator at source commit `970a393c384a268021af8cffb3780b520c7f48d4` (normalized public/local file comparison matched), the local middleware manual and implementation, seven local DBMM decks, and installed definitions for F-16C, F-5E, M-2000C and JF-17. The middleware working tree has unrelated local changes; it was read only and those changes were preserved. User-supplied video links are included as walkthroughs; video content could not be fetched and was not used as API evidence.

A necessary catalog correction distinguishes serialized `ActionSetServerVariable` from its plural internal `ActionId`. Event maps and catalog keys now use implementation names; helper lookup preserves the older ID as an alias. This is a skill/catalog fix, not a MATRIC code change. The catalog was refreshed against the same identified MATRIC assembly; its version remains deck format 3.

Offline acceptance covers 15 tests, including all five DCS-BIOS input interface forms, alias/definition selection, unsupported commands/newline rejection, feedback dependencies, empty mailbox initialization and packaging. The synthetic DCS deck passed native MATRIC import/export/reimport with its five command actions, four feedback bindings and empty mailbox preserved. The generic starter also passed its native regression check. Generated JavaScript was checked separately with an installed F-16 `ICP_HUD_BRT_KNB` definition for endpoints, midpoint, clamping, invalid input and inverse feedback scaling; no commands were sent.

Existing DBMM examples are not treated as golden fixtures: several contain legacy switch/applet events and saved mailbox values that fail current checks. The guide explains those limits. The inspected MATRIC importer preserves `ReferencedUserVariables` metadata but does not install calculated user variables; users must configure those explicitly or use direct binding transforms. DBMM owns runtime telemetry and creates its mailbox at startup.

Remaining live acceptance: verify aircraft/seat identifiers, command direction, momentary release, cockpit-originated feedback, display formatting, DBMM variable selection/aliases, slider behavior and repeat-command timing. Neither DCS nor a live middleware session was operated. Helper audits do not evaluate arbitrary JavaScript, prove dynamically constructed dependencies, or guarantee mailbox delivery. Run DCS native acceptance with `tests/test-native-import.ps1 -Scenario dcs` and an explicitly supplied build when needed.

Version 0.2.0 is [published](https://github.com/tgudelj/matric-deck-skill/releases/tag/v0.2.0) from implementation commit `fe6e77c`. Windows/Linux CI passed for the [main push](https://github.com/tgudelj/matric-deck-skill/actions/runs/40037251358) and [release tag](https://github.com/tgudelj/matric-deck-skill/actions/runs/40037253624). Public release bytes/checksum and installation from the tagged GitHub directory were verified. The active local Codex skill was updated after verifying that its v0.1.0 files had no local customizations. MATRIC's working tree remains clean. The one-time scheduling automation was removed when this implementation began.

## Client-scaling authoring guidance (unreleased)

The installable skill now warns against using a painted page background and separate controls to construct pixel-perfect panels. Core guidance favors control-owned labels, bezels, backgrounds and rotary images, with plain or non-alignment-dependent page decoration. The deck-format reference explains why matching Cols/Rows or an authoring image's resolution is insufficient, and preview guidance distinguishes static composition from client rendering.

This follows maintainer feedback and a read-only inspection of `desktop/matric-vue-client/src/components/clientPage.vue` in the separate MATRIC checkout: its page container is viewport-sized, its logical grid uses the smaller viewport-per-column/per-row dimension, control cell size is floored, and page background sizing is handled separately by CSS. No MATRIC application code was changed or copied into the skill. Earlier UFC previews remain offline approximations; their painted labels and fascia are not evidence of portable alignment and would need a separate rework to follow this guidance. This is an unreleased instruction/reference change; `VERSION` remains 0.2.0 and no new native/live compatibility is claimed.

All 15 independent tests and test packaging passed. The skill-creator validator could not start because PyYAML was unavailable; separate checks passed for the existing frontmatter fields, local reference links/section anchor, packaged guidance bytes, checksum and matching license copies. No dependency was added to the portable helpers.

## Native control-selection guidance (unreleased)

The skill now prefers native selectors, encoders and absolute-value controls when they match the requested interaction, instead of emulating them with banks of buttons. The native action recipes describe multi-position switch state images/defaults/orientation, zero-based state mapping, `state.position` feedback, and the need to use either generic or specific transition events without double-sending commands. The rotary recipe records verified clockwise/counterclockwise events and the image/size/center-hit-area settings needed for a usable native encoder. Evidence is the bundled catalog and read-only inspection of the corresponding MATRIC Vue controls; no MATRIC application code was changed or distributed. This remains an unreleased instruction update with `VERSION` at 0.2.0.

All 15 independent tests, skill packaging, example validation, and the native switch/encoder method simulations passed. The native simulations are isolated offline checks, not native import or live DCS acceptance.

## Local F/A-18C UFC authoring exercise (2026-10-24)

A generated example in the ignored `.qa/f18-ufc` directory exercises the existing skill against installed `FA-18C_hornet` definitions: 54 native controls, 69 literal DBMM command actions, 28 momentary press/release pairs and 19 feedback outputs. It includes original SVG controls, a generated metal texture, editable deck sources, an importable deck and a DBMM variable-selection companion whose dictionary-of-string-arrays format was checked against the middleware importer. No aircraft definitions, user decks or MATRIC binaries were added to the distributable payload. The 4:3 tablet layout uses step buttons for rotary controls and approximate monospace display glyphs.

Deck/archive validation and the DCS audit passed; the audit retains its general unevaluated-JavaScript warning. Separate JavaScript checks passed for all 16 binding transforms and all momentary command pairs. All 15 independent tests and skill packaging passed using a repository-local temporary directory to avoid sandbox system-temp permissions. The preview was visually inspected as an approximation; native import and live DCS/DBMM operation were not tested. This authoring exercise does not change the installed skill or its release version.

The local graphics revision in `.qa/f18-ufc-v2` follows a supplied UFC photograph: gray fluted VOL/BRT knobs and cup-shaped COMM knobs use generated transparent sprites; SVG keys now have recessed faces and raised square guards, option/I-P buttons are round, and the panel has muted olive-charcoal paint and screwed display fascias. Deck/page/control identities and every command/binding are preserved from the first example. The pointer marks are static artwork; percentage readouts remain the position feedback and step-button interaction is unchanged. The source photograph is not distributed. This is a generated example revision, not a skill release or a new live-compatibility claim.

Revision 3 in `.qa/f18-ufc-v3` changes both rotary sprites to an orthographic overhead view, with the fluted knob face and COMM cup centered on their circular shaft axes. It retains the v2 panel layout and bindings. The generated full-resolution images, transparent deployment sprites, prompts and editable deck source accompany the v3 package. This remains an offline graphics revision with static pointer artwork.

Revision 4 in `.qa/f18-ufc-v4` uses the newer supplied reference to replace the earlier green-tinted hardware palette with neutral anthracite gray. Native SVG paint, keys, guards, legends, screws and fascia are recolored; SVG filters desaturate the existing metal texture and neutralize/darken the overhead knob images. Green is retained inside the displays. This is an appearance-only update: the neutral page fallback color is the only deck-configuration change, and all identities, actions, feedback bindings, layout and DBMM output requirements remain unchanged. Raster source images and the installable skill payload are preserved.

Revision 5 in `.qa/f18-ufc-v5` changes the page from 64 × 48 to 67 × 40 cells, with a 1340 × 800 landscape canvas based on the documented 9-inch Lenovo Tab M9 screen. The diagonal alone does not establish aspect ratio; this is a representative target in the absence of an exact tablet model. Controls and background geometry are reflowed together, preserving circular rotaries, square keycaps and the anthracite palette. EM CON is relocated to the lower-right area. All 54 control identities, 69 command actions and 19 feedback requirements are retained; this adds no native/live-compatibility claim and does not change the skill release version.

Revision 6 in `.qa/f18-ufc-v6` removes the three non-cockpit VOL/BRT percentage windows and replaces their six step buttons and static knob faces with three native `MCRotaryEncoder` controls. The bundled catalog and the local `MCRotaryEncoder.vue` renderer establish `clockwise`/`counterclockwise` events, `DialImage`, `DialSize`, `Ticks` and the center-button hit area. Each direction writes a verified ±3200 variable-step command to DBMM; `ButtonSize: 0` leaves the dial surface available for dragging. The deck now has 48 controls, the same 69 command actions, and 16 feedback outputs. The relative encoder angle tracks local interaction rather than absolute DCS state. Offline simulations of the actual component methods passed for clockwise/counterclockwise touch gestures on all three encoders. Retained button IDs/bindings, all cockpit command configurations, and the 67 × 40 layout are preserved. Native import and live DCS/DBMM operation remain untested; no MATRIC code or installed skill files were changed.

Revision 7 in `.qa/f18-ufc-v7` replaces the three ADF buttons with one vertical `MCThreePositionSwitch`. Its three control-owned state images show 1/OFF/2 from top to bottom. Because the native top half increments, native indices 0/1/2 map to DCS states 2/1/0; the same inverse mapping drives `state.position` feedback. Four specific transition events send absolute DCS states, with no generic-event actions. The deck now has 46 controls, 70 action configurations and the same 16 required outputs. Offline simulations of the native switch cover all four adjacent transitions, both end stops, one command per change and feedback without command echoes; live DCS behavior remains untested. Retained controls/encoder bindings and the page identity/layout are preserved. Page-painted decoration elsewhere in the earlier example remains a separate responsive-layout limitation.

## Resume on another machine

Clone the standalone repository, read `AGENTS.md` and `skills/matric-decks/SKILL.md`, and run the tests and packager described in the README. No MATRIC checkout, Windows desktop compiler or external Python packages are required for that workflow. Work on the skill here; do not restore it into the MATRIC application repository.

The local installed copy in Codex's user skills directory is an installation, not the development source. Update that copy after validating a change or install a tagged release from GitHub. Never silently overwrite local customizations.

## Refresh compatibility metadata

On Windows, obtain an explicitly identified MATRIC desktop build and a Visual Studio C# compiler, then run:

```powershell
./tools/refresh-matric-catalog.ps1 -DesktopBin 'C:/path/to/MATRIC/build' -MatricSourceCommit '<MATRIC source commit>'
```

The exporter loads configuration definitions and serializes templates; it does not run actions. It records the supplied MATRIC commit and the actual `MatricPro.dll` SHA-256. If the source commit is unknown, leave it as `unknown`; do not substitute this skill repository's commit. Keep binaries outside this repository.

Review changes to templates, properties, enum encodings, events and key codes. Run the offline tests, then check native import when the necessary build is available. The helper intentionally maps the native touchpad's legacy constructor event to `touchpad`, matching its definition/client. Opaque plugin settings and applet-defined events require their own integration evidence.

## Optional native import check

```powershell
python skills/matric-decks/scripts/deck_tool.py pack skills/matric-decks/assets/starter --output .qa/starter.deck
./tests/test-native-import.ps1 -Package .qa/starter.deck -DesktopBin 'C:/path/to/MATRIC/build'
```

This compiles the small checker against the supplied build, copies dependencies into an owned temporary directory, and imports only into isolated collections. It exports and reimports the starter, checks the configuration/resource round trip, and removes its own temporary directory. It never starts MATRIC or executes controls. Run it only against a trusted local build.

## Release

Update `VERSION`, run independent tests and relevant optional compatibility checks, then run `python tools/package_skill.py`. Review the resulting ZIP and checksum. Publish a matching `v<version>` Git tag and GitHub release with those two files. GitHub's source archive is a developer checkout; the versioned skill ZIP is the installable payload. A public repository does not automatically list a skill in a plugin directory.
