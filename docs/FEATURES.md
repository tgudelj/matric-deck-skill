# Features and compatibility

This guide describes the published v0.7.0 skill. AI authoring instructions and detailed workflows live in [the installable skill](../skills/matric-decks/SKILL.md).

## Setup, handover and revision checks

The portable `workflow_tool.py` helper provides three read-only authoring commands:

- `setup` checks the installed payload and selected OBS, game-profile or DCS definition inputs. An explicit OBS endpoint can use live read-only discovery. Reports distinguish checked facts, user confirmations, unresolved prerequisites and blocked checks; they do not infer that MATRIC integrations work.
- `handover` explains a final deck's controls, declared feedback, dependencies and unresolved setup. Structural validation is separate from recorded visual, import, device and live-test evidence. Evidence is bound to the exact deck and supplied applet bytes. JSON reports retain input fingerprints for later revisions.
- `compare` reports changed layout, artwork, actions, feedback, dependencies, identities and unknown data. An optional baseline handover rechecks recorded profile/definition/applet files. `--presentation-only` returns nonzero when changes outside known presentation fields or recorded-source drift require review.

Both Markdown and JSON output are available. Reports stay outside staged decks, and existing report files are never overwritten. These tools execute no actions or scripts and require neither MATRIC binaries nor a source checkout. They supplement the existing OBS defaults and cockpit visual-reference research. See [commands, evidence and limitations](../skills/matric-decks/references/workflow-reports.md).

Markdown reports lead with plain-language results and next steps. Technical IDs, hashes and field paths are kept in expandable details. Checks not covered in the report say "Not checked here yet"; failed checks say "Needs fixing." JSON retains the same status codes for other tools.

## OBS discovery

For OBS, the skill includes a standard-library WebSocket 5 client that reads the active collection, scenes, groups, sources, filters, transitions, audio state and output activity. Supply the enabled OBS WebSocket endpoint; authenticated connections use a password environment variable or a private interactive prompt. The helper sends only read-only discovery requests. Exported/saved collection JSON remains available for offline discovery, inactive collections and saved keyboard bindings. See [OBS discovery](../skills/matric-decks/references/obs-discovery.md) for commands and snapshot limits. Execution of native MATRIC OBS actions still requires MATRIC's OBS integration.

## DCS cockpit decks

The same skill supports Digital Combat Simulator panels through DCS-BIOS and DCS-BIOS-MATRIC-Middleware (DBMM). It reads installed aircraft definitions, builds native command-variable actions and simulator feedback bindings, audits required outputs, and provides an original synthetic example. Start with the [DCS setup and authoring guide](../skills/matric-decks/references/dcs-bios.md). Live operation needs DCS, DCS-BIOS, DBMM and MATRIC configured; static checks do not prove cockpit behavior.

```text
Use the matric-decks skill to build an F-16C ICP panel using my installed
DCS-BIOS definitions, with simulator feedback and a DBMM output checklist.
```

## Application input discovery

The skill reads user input profiles for Microsoft Flight Simulator 2020/2024, X-Plane 11/12, Kerbal Space Program, Star Citizen, Elite Dangerous, Euro Truck Simulator 2, Farming Simulator, iRacing and Assetto Corsa Competizione, with native keyboard/vJoy action candidates and profile/context checks. The shared workflow maps configured application inputs to MATRIC keyboard/vJoy actions regardless of genre; per-application references document formats and limits. Read [the application input guide](../skills/matric-decks/references/application-inputs.md) for discovery commands, virtual-device correspondence and supported file formats. This input-only workflow does not provide game-state feedback. Star Citizen overrides can omit defaults, and MSFS active profile layers need confirmation. X-Plane discovery reads saved keyboard/joystick `.prf` assignments; active profiles, aircraft associations, numeric axis functions and device correspondence require confirmation.

```text
Use the matric-decks skill to make an Elite Dangerous ship-systems deck
for my portrait phone using my selected bindings and MATRIC vJoy device.
```

## Package and test

From the repository root:

```text
python -B -m unittest discover -s tests -p "test_*.py" -v
python -B tools/package_skill.py
```

Packaging produces `dist/matric-decks-<version>.zip` and a `.sha256` checksum file. It includes only the installable skill folder, not developer tools, test artifacts or MATRIC binaries. Existing release files are not overwritten. Change `VERSION` before producing a new release.

See [development and compatibility](DEVELOPMENT.md) for optional catalog refresh and native MATRIC import checks. Ordinary tests and packaging require neither MATRIC source nor a MATRIC build. CI is configured for Windows and Linux.

## Custom applets

When native controls do not fit the requested interaction, the skill can author HTML/CSS/JavaScript applets, validate manifests and deck bindings, and produce a separate importable `.mapl` alongside the `.deck`. It includes an original history-inspector starter and a synthetic integrated example. Read the [custom applet workflow](../skills/matric-decks/references/custom-applets.md) for the message API, installation, responsive design and target-version limits.

```text
python skills/matric-decks/scripts/applet_tool.py example --output /path/to/history-demo
node --test tests/applet-runtime.test.cjs
```

Applet helpers use standard-library Python. The starter runs directly in a browser without npm packages; Node is only needed for the independent JavaScript tests. Native controls remain the preferred starting point.

## Compatibility

The bundled catalog covers deck format 3, with 21 native control definitions and 35 action definitions. The catalog records its MATRIC source commit and assembly hash; those are compatibility provenance, not this skill's version. Structural validation does not prove application shortcuts, target devices, external integrations or appearance on every screen.

Stream Deck plugin support remains experimental. Opaque plugin configurations and resources need MATRIC-specific verification; plugin installations and global settings are not bundled. Existing MATRIC compatibility exclusions remain in effect. See [the skill instructions](../skills/matric-decks/SKILL.md).


## Additional calculation resources

Declare dynamic native-control assets with `Config.AdditionalResources` and select filenames using `resources["key"]` in property bindings. The helper validates keys, paths and file presence; the included synthetic example demonstrates three image states. Resource-map support requires an updated MATRIC server/client, independently of deck format and this skill version. Older servers may delete the declarations/files when saving. See [the resource reference](../skills/matric-decks/references/deck-format.md#additional-calculation-resources).

Optional native verification of the synthetic resource example uses the developer-only checker: pack `skills/matric-decks/assets/additional-resources` to a temporary `.deck`, then run `tests/test-native-import.ps1 -Package <example.deck> -DesktopBin <explicit-feature-build> -Scenario resources`. It uses isolated collections, checks save retention and byte-preserving export/reimport, and executes no actions.
