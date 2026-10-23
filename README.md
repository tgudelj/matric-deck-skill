# MATRIC Deck Skill

Create editable MATRIC control decks and importable `.deck` packages with an AI assistant, without operating the MATRIC editor. Includes format and action references, native control templates, a validator/packager, and offline OBS scene-collection discovery.

This project is developed, versioned and released independently of MATRIC. Using the skill requires Python 3.11 or newer; its helpers use only the standard library. A MATRIC installation is needed to import and use the finished deck. MATRIC source code and binaries are not distributed here.

## Install

In Codex, ask the skill installer:

```text
$skill-installer install https://github.com/tgudelj/matric-deck-skill/tree/main/skills/matric-decks
```

Alternatively, download a versioned `matric-decks-<version>.zip` from this repository's releases. Extract its `matric-decks` folder into your Codex user skills directory (`$CODEX_HOME/skills`, normally `~/.codex/skills`). The result must contain `matric-decks/SKILL.md` directly. Keep the included scripts, references, assets and license together. For an update, replace the old skill folder after preserving any local changes; installing a skill does not update generated decks.

Codex normally detects local skill changes automatically; restart it if the skill does not appear. See the [official skill documentation](https://learn.chatgpt.com/docs/build-skills). The instructions follow the Agent Skills directory format; compatibility with another assistant depends on its skill loader and ability to run Python helpers. This repository currently distributes a plain skill, rather than a hosted service or a plugin-directory entry.

## Use

```text
Use $matric-decks to make a 6-by-4 landscape deck with copy, paste,
media controls and a second page for text snippets. Package it for import.
```

For OBS, supply an exported scene collection JSON or the path to your saved collection directory. The bundled reader discovers collections, scenes, groups, sources, filters and saved shortcuts without connecting MATRIC to OBS. Saved configuration is not live state. Direct read-only obs-websocket discovery is documented separately; no live WebSocket client is bundled. Execution of native MATRIC OBS actions still requires MATRIC's OBS integration.

The assistant produces editable JSON/assets and a `.deck` archive. Review the configured actions and external dependencies, then import the `.deck` using MATRIC's normal import workflow. The skill does not execute controls or install a deck into a live library.

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
