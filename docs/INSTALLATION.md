# Install MATRIC Deck Skill

The installable payload is the same for all assistants below: a `matric-decks` directory containing `SKILL.md`, `scripts`, `references`, `assets` and `LICENSE.txt`. Keep the entire directory together. `agents/openai.yaml` supplies Codex-specific UI metadata; the other assistants use `SKILL.md` and its supporting files.

Install Python 3.11 or newer in the environment where the assistant runs, and allow it to run the helper commands when requested. There are no external Python packages to install. MATRIC is needed to use the generated deck, but is not needed to generate it.

The paths and host commands below follow the linked vendor documentation. The helper scripts and native MATRIC import have been tested; end-to-end operation in Claude Code, Cursor, Copilot and Gemini CLI has not been tested by this project.

## Choose an installation scope

Download `matric-decks-0.3.0.zip` and its checksum from the [v0.3.0 release](https://github.com/tgudelj/matric-deck-skill/releases/tag/v0.3.0). Extract it, then place the `matric-decks` directory in one of these locations:

| Assistant | Personal installation | Project installation |
| --- | --- | --- |
| Codex | `~/.codex/skills/matric-decks/` | `.agents/skills/matric-decks/` |
| Claude Code | `~/.claude/skills/matric-decks/` | `.claude/skills/matric-decks/` |
| Cursor | `~/.cursor/skills/matric-decks/` | `.cursor/skills/matric-decks/` |
| GitHub Copilot | `~/.copilot/skills/matric-decks/` | `.github/skills/matric-decks/` |
| Gemini CLI | `~/.gemini/skills/matric-decks/` | `.gemini/skills/matric-decks/` |

`~` means your home directory: `%USERPROFILE%` on Windows, commonly `C:Usersyour-name`. Project paths are relative to the project in which you run the assistant. Personal installations are available across local projects; project installations can be committed for teammates. Choose a writable deck-authoring project; you do not need a MATRIC source checkout.

The final path should be, for example, `~/.claude/skills/matric-decks/SKILL.md`, with no extra `matric-decks` directory nested inside it. Copy the extracted skill folder, not this repository's entire source archive. If cloning the repository instead, the installable folder is `skills/matric-decks`.

For cloud or remote agents, put the skill and Python in the environment where the agent actually runs, using the vendor's supported project or sync mechanism. A local personal installation does not automatically reach remote workers. Provide an exported OBS collection explicitly if that environment cannot read your local OBS files.

## Codex

Ask Codex's skill installer to install the tagged skill directory:

```text
$skill-installer install https://github.com/tgudelj/matric-deck-skill/tree/v0.3.0/skills/matric-decks
```

Alternatively, use the folder location above. If `CODEX_HOME` is customized, its `skills` directory replaces `~/.codex/skills`. Invoke with `$matric-decks`, or describe a MATRIC deck task. Codex detects skill changes automatically; restart if it does not appear. [Official skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Claude Code

Copy the extracted folder into the personal or project location above. In Claude Code, run:

```text
/matric-decks Create a 6-by-4 landscape deck with copy, paste and a text page.
```

Claude can also select the skill when a request matches its description. Use `/skills` to check availability. If you created a skills root that was absent when the session started, use `/reload-skills`, or start a new session. Local personal folders are not automatically available in Cowork or cloud sessions; use Anthropic's account/project mechanisms for those environments. [Official Claude Code skill documentation](https://code.claude.com/docs/en/skills).

## Cursor

Copy the complete folder into the personal or project location above. Open Agent chat, type `/`, and select `matric-decks`; then describe the deck to create. A matching plain-language request can also cause automatic selection. If the new skill is missing, start a new Agent session.

Cursor's **From GitHub Repository** import expects plugin/marketplace packaging. This repository is a plain skill, so use folder installation rather than that import flow. Personal local skills are not automatically available to every cloud/remote worker; use Cursor's supported sync or a project installation where appropriate. [Official Cursor skill documentation](https://cursor.com/docs/skills).

## GitHub Copilot

Copy the folder into the personal or project location above, then use Copilot CLI or an IDE's agent mode. For a cloud agent, commit a project installation in the repository it works on. Skill support depends on the IDE version and organizational settings. Ask:

```text
Use the matric-decks skill to create an OBS scene-control deck from this exported collection.
```

Copilot selects relevant skills from the request and skill description. [Official Copilot skill locations and supported surfaces](https://docs.github.com/en/copilot/concepts/customizations/agent-skills).

As an alternative to copying files, GitHub CLI 2.90.0+ provides the preview `gh skill` commands:

```sh
gh skill preview tgudelj/matric-deck-skill matric-decks
gh skill install tgudelj/matric-deck-skill matric-decks@v0.3.0 --scope user
```

These commands default to Copilot; `--scope user` chooses a personal installation. For older CLI versions, use the folder instructions. [Official GitHub CLI skill installation guidance](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills).

## Gemini CLI

Install the skill subdirectory from GitHub:

```sh
gemini skills install https://github.com/tgudelj/matric-deck-skill.git --path skills/matric-decks --scope user
```

This follows the repository's default branch. For the fixed v0.3.0 payload, use the release ZIP and folder location above instead. To install only for the current project, use `--scope workspace` or the project folder.

Inside Gemini CLI, run `/skills reload` and `/skills list`, then request a deck using the `matric-decks` skill by name. Complete Gemini's installation/activation prompts when shown. [Official Gemini skill locations and install options](https://geminicli.com/docs/cli/skills/), [skill management](https://geminicli.com/docs/cli/using-agent-skills/).

## Verify the installation

From the installed `matric-decks` directory, run:

```sh
python --version
python scripts/deck_tool.py catalog --action ActionHotkey
python scripts/deck_tool.py validate assets/starter
```

Use `python3` or `py -3.11` if that is how Python 3.11+ is available on your machine. The starter should report no validation errors. This checks the installed files and Python runtime; it does not prove the assistant has discovered the skill.

Next, ask the assistant to use `matric-decks` to create a small deck and return the `.deck` package. Approve ordinary file/terminal operations as appropriate for your environment. Review the actions and import the result through MATRIC's normal workflow. Discovery of saved OBS configuration is independent of MATRIC, while execution of native OBS actions still needs MATRIC's OBS connection.

## Update or remove

For folder installations, preserve any local customizations, then replace the complete old `matric-decks` folder with the new release's folder. Do not merge a new release into an old installation; obsolete files could remain. Reload skills or start a new session as needed. Remove that folder to uninstall a manual installation. Installing or removing a skill does not change decks already generated or imported.

For an installation managed by a harness's installer, use its documented update/uninstall workflow. Gemini provides `gemini skills uninstall matric-decks`; `gh skill` provides its own update workflow. A tagged version is useful when you want reproducible authoring; the repository's default branch receives ongoing development.
