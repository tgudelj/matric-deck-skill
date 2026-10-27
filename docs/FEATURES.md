# Features and compatibility

This guide describes the published release and features in the development skill. AI authoring instructions and detailed workflows live in [the installable skill](../skills/matric-decks/SKILL.md).

## OBS discovery (development skill)

For OBS, the development skill includes a standard-library WebSocket 5 client that reads the active collection, scenes, groups, sources, filters, transitions, audio state and output activity. Supply the enabled OBS WebSocket endpoint; authenticated connections use a password environment variable or a private interactive prompt. The helper sends only read-only discovery requests. Exported/saved collection JSON remains available for offline discovery, inactive collections and saved keyboard bindings. See [OBS discovery](../skills/matric-decks/references/obs-discovery.md) for commands and snapshot limits. This capability is not in the published v0.2.0 package. Execution of native MATRIC OBS actions still requires MATRIC's OBS integration.

## DCS cockpit decks

The same skill supports Digital Combat Simulator panels through DCS-BIOS and DCS-BIOS-MATRIC-Middleware (DBMM). It reads installed aircraft definitions, builds native command-variable actions and simulator feedback bindings, audits required outputs, and provides an original synthetic example. Start with the [DCS setup and authoring guide](../skills/matric-decks/references/dcs-bios.md). Live operation needs DCS, DCS-BIOS, DBMM and MATRIC configured; static checks do not prove cockpit behavior.

```text
Use the matric-decks skill to build an F-16C ICP panel using my installed
DCS-BIOS definitions, with simulator feedback and a DBMM output checklist.
```

## Flight and space sim inputs (development skill)

The development skill reads user input profiles for Microsoft Flight Simulator 2020/2024, Star Citizen and Elite Dangerous, with native keyboard/vJoy action candidates and profile/context checks. It focuses on auxiliary controls such as throttle, flaps, mixture, radiators and ship systems. Read [the game input guide](../skills/matric-decks/references/game-inputs.md) for discovery commands, virtual-device correspondence and supported file formats. This input-only workflow does not provide game-state feedback. Star Citizen overrides can omit defaults, and MSFS active profile layers need confirmation. These additions are not in the published v0.2.0 release.

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

## Custom applets (development skill)

When native controls do not fit the requested interaction, the development skill can author HTML/CSS/JavaScript applets, validate manifests and deck bindings, and produce a separate importable `.mapl` alongside the `.deck`. It includes an original history-inspector starter and a synthetic integrated example. Read the [custom applet workflow](../skills/matric-decks/references/custom-applets.md) for the message API, installation, responsive design and target-version limits. These additions are not included in the published v0.2.0 release.

```text
python skills/matric-decks/scripts/applet_tool.py example --output /path/to/history-demo
node --test tests/applet-runtime.test.cjs
```

Applet helpers use standard-library Python. The starter runs directly in a browser without npm packages; Node is only needed for the independent JavaScript tests. Native controls remain the preferred starting point.

## Compatibility

The bundled catalog covers deck format 3, with 21 native control definitions and 35 action definitions. The catalog records its MATRIC source commit and assembly hash; those are compatibility provenance, not this skill's version. Structural validation does not prove application shortcuts, target devices, external integrations or appearance on every screen.

Stream Deck plugin support remains experimental. Opaque plugin configurations and resources need MATRIC-specific verification; plugin installations and global settings are not bundled. Existing MATRIC compatibility exclusions remain in effect. See [the skill instructions](../skills/matric-decks/SKILL.md).

