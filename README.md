# MATRIC Deck Skill

Create editable MATRIC control decks and importable `.deck` packages with an AI assistant, without operating the MATRIC editor. Includes format and action references, native control templates, a validator/packager, live and offline OBS discovery, and DCS-BIOS/DBMM command and feedback authoring.

This project is developed, versioned and released independently of MATRIC. Using the skill requires Python 3.11 or newer; its helpers use only the standard library. A MATRIC installation is needed to import and use the finished deck. MATRIC source code and binaries are not distributed here.

## Install

The same skill folder works with assistants that support Agent Skills and can run its Python helpers. Start with the [installation guide](docs/INSTALLATION.md), which covers:

- [Codex](docs/INSTALLATION.md#codex)
- [Claude Code](docs/INSTALLATION.md#claude-code)
- [Cursor](docs/INSTALLATION.md#cursor)
- [GitHub Copilot](docs/INSTALLATION.md#github-copilot)
- [Gemini CLI](docs/INSTALLATION.md#gemini-cli)

For a quick Codex installation:

```text
$skill-installer install https://github.com/tgudelj/matric-deck-skill/tree/v0.2.0/skills/matric-decks
```

You can also download the versioned `matric-decks-<version>.zip` from [Releases](https://github.com/tgudelj/matric-deck-skill/releases), then extract the complete `matric-decks` folder into your assistant's skills directory. The guide lists personal and project locations, invocation examples, verification and update steps. This repository distributes a plain skill; it is not registered in a plugin directory.

## Use

```text
Use the matric-decks skill to make a 6-by-4 landscape deck with copy, paste,
media controls and a second page for text snippets. Package it for import.
```

For OBS, the development skill includes a standard-library WebSocket 5 client that reads the active collection, scenes, groups, sources, filters, transitions, audio state and output activity. Supply the enabled OBS WebSocket endpoint; authenticated connections use a password environment variable or a private interactive prompt. The helper sends only read-only discovery requests. Exported/saved collection JSON remains available for offline discovery, inactive collections and saved keyboard bindings. See [OBS discovery](skills/matric-decks/references/obs-discovery.md) for commands and snapshot limits. This capability is not in the published v0.2.0 package. Execution of native MATRIC OBS actions still requires MATRIC's OBS integration.

The assistant produces editable JSON/assets and a `.deck` archive. Review the configured actions and external dependencies, then import the `.deck` using MATRIC's normal import workflow. The skill does not execute controls or install a deck into a live library.

## DCS cockpit decks

The same skill supports Digital Combat Simulator panels through DCS-BIOS and DCS-BIOS-MATRIC-Middleware (DBMM). It reads installed aircraft definitions, builds native command-variable actions and simulator feedback bindings, audits required outputs, and provides an original synthetic example. Start with the [DCS setup and authoring guide](skills/matric-decks/references/dcs-bios.md). Live operation needs DCS, DCS-BIOS, DBMM and MATRIC configured; static checks do not prove cockpit behavior.

```text
Use the matric-decks skill to build an F-16C ICP panel using my installed
DCS-BIOS definitions, with simulator feedback and a DBMM output checklist.
```

## Package and test

From the repository root:

```text
python -B -m unittest discover -s tests -p "test_*.py" -v
python -B tools/package_skill.py
```

Packaging produces `dist/matric-decks-<version>.zip` and a `.sha256` checksum file. It includes only the installable skill folder, not developer tools, test artifacts or MATRIC binaries. Existing release files are not overwritten. Change `VERSION` before producing a new release.

See [development and compatibility](docs/DEVELOPMENT.md) for optional catalog refresh and native MATRIC import checks. Ordinary tests and packaging require neither MATRIC source nor a MATRIC build. CI is configured for Windows and Linux.

## Compatibility

The bundled catalog covers deck format 3, with 21 native control definitions and 35 action definitions. The catalog records its MATRIC source commit and assembly hash; those are compatibility provenance, not this skill's version. Structural validation does not prove application shortcuts, target devices, external integrations or appearance on every screen.

Stream Deck plugin support remains experimental. Opaque plugin configurations and resources need MATRIC-specific verification; plugin installations and global settings are not bundled. Existing MATRIC compatibility exclusions remain in effect. See [the skill instructions](skills/matric-decks/SKILL.md).

## License

This repository's code, instructions, generated catalog and starter assets are licensed under [MIT](LICENSE). This license does not change the licenses of MATRIC, OBS Studio, Elgato software, third-party plugins or external material linked from the documentation.
