# Development and compatibility

## Current state

Initial version: 0.1.0, extracted into a separate project on 2026-10-23. The installed skill includes instructions, deck/action/OBS references, a catalog of actual MATRIC definitions, standard-library Python helpers, and a two-page starter deck with an SVG background. Runtime authoring and ordinary testing are independent of the MATRIC source tree.

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
