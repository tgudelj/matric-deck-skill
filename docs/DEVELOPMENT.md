# Development and compatibility

## Current state

Initial version: 0.1.0, extracted into a separate project on 2026-10-23. The installed skill includes instructions, deck/action/OBS references, a catalog of actual MATRIC definitions, standard-library Python helpers, and a two-page starter deck with an SVG background. Runtime authoring and ordinary testing are independent of the MATRIC source tree.

The original acceptance run passed eight offline tests and MATRIC's native import â†’ export â†’ reimport check, preserving two pages, five controls, hotkey configuration and the bundled SVG. OBS discovery was also exercised against a local saved collection; that user configuration is not part of this repository. Repository extraction adds a packaging acceptance test and cross-platform CI configuration. Local standalone validation passed all nine tests, release packaging/checksum verification, native import/export/reimport, and catalog refresh against the identified MATRIC build. GitHub CI passed on Windows and Linux for the initial push and release tag: [main run](https://github.com/tgudelj/matric-deck-skill/actions/runs/40028705824), [v0.1.0 run](https://github.com/tgudelj/matric-deck-skill/actions/runs/40028707247).

The public [v0.1.0 release](https://github.com/tgudelj/matric-deck-skill/releases/tag/v0.1.0) is published under MIT. Its downloaded ZIP and SHA-256 were verified, and installation from the tagged GitHub skill directory was checked against the release source. The active local skill installation was updated from that version. The previous skill additions and manual edits were removed from the MATRIC working tree, leaving it clean.

Saved OBS discovery is implemented. Direct read-only obs-websocket discovery is described in the guide; a live client is not implemented. A rendered MATRIC-client preview is also not implemented. Preserve this distinction in user-facing claims.

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
