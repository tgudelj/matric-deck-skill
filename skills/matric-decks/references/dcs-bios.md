# DCS decks with two-way DBMM integration

Use this workflow for Digital Combat Simulator panels that send cockpit commands and display actual simulator state. Keep it inside the existing MATRIC deck workflow: DBMM integration uses native variable actions and bindings, so it does not require a separate skill, MCP server or Stream Deck plugin.

## Establish the aircraft and setup

Ask for the exact DCS aircraft/variant, desired panels, device layout and installed DCS-BIOS definition directory. Do not infer cockpit identifiers, switch positions, seat-specific controls or command support from a screenshot or a different aircraft. Separate a keyboard-only deck from a DBMM-backed panel when the user asks for one; FC3 and other modules can expose different subsets of cockpit functionality.

1. Install [DCS-Skunkworks DCS-BIOS](https://github.com/DCS-Skunkworks/dcs-bios#installation) in the active DCS Saved Games profile. Preserve existing `Scripts/Export.lua` integrations; merge the documented DCS-BIOS hook instead of replacing another exporter. The game installation directory is not the Saved Games profile.
2. Locate `Scripts/DCS-BIOS/doc/json` under that profile, commonly `%USERPROFILE%\Saved Games\DCS\Scripts\DCS-BIOS\doc\json`. Older installations may use `DCS.openbeta`; custom profiles differ. Use definitions matching the user's installed DCS-BIOS version and modules, rather than a stale online snapshot. Missing generated definitions may require running DCS with that aircraft as described by DCS-BIOS.
3. Install [DCS-BIOS-MATRIC-Middleware (DBMM)](https://github.com/tgudelj/DCS-BIOS-MATRIC-Middleware/releases). Choose a standalone build or install the runtime required by its framework-dependent build. Select the actual `doc/json` directory in DBMM.
4. Enable third-party integration in MATRIC settings and restart MATRIC if required. DBMM reads MATRIC's integration port from MATRIC's configuration; do not substitute the mobile-client port. Confirm the installed MATRIC/DBMM versions are compatible.
5. Configure DBMM's exported variables for the aircraft, including all feedback and calculated-variable dependencies. Its normal DCS-BIOS defaults are multicast `239.255.50.10:5010` for telemetry and UDP port `7778` for commands. Match an existing customized configuration rather than changing it silently.
6. Start DBMM and a DCS mission with the intended aircraft. Confirm MATRIC receives variables such as `dcs__ACFT_NAME` and the required aircraft outputs. Import the generated `.deck` only after reviewing its actions and dependencies. Authoring can happen offline; live validation needs the simulator, MATRIC and DBMM.

The skill never installs or starts those applications, edits exporter configuration, or operates the cockpit just to inspect definitions. The [DBMM repository and bundled manual](https://github.com/tgudelj/DCS-BIOS-MATRIC-Middleware) describe the setup UI. User-supplied [tutorial 1](https://www.youtube.com/watch?v=c3Zrvx_MjR4) and [tutorial 2](https://www.youtube.com/watch?v=eXult3xushI) are additional visual walkthroughs; code and installed definitions establish the exact formats below.

## Cockpit layout and reference decks

Use user-provided decks to understand their workflow and preferred appearance, not as a universal aircraft template. Inspect the actual export when available. If using a similarly titled installed deck instead, disclose the substitution; title alone does not establish that it matches the supplied revision. Keep the reference and its artwork local unless redistribution is explicitly authorized.

Prioritize the user's tasks and touch interaction over physical cockpit fidelity. A touchscreen lacks the tactile distinction, detents and landmarks of hardware, and a tablet may be much smaller than the actual panel, including an up-front controller. Copying every control's shape, spacing and position can therefore make operation harder. Follow an explicitly requested replica style, but adapt its touch targets and discuss material usability tradeoffs rather than assuming visual accuracy establishes a good experience.

- Group controls by the user's workflow even when they occupy different consoles or panels in the real aircraft. Vintage aircraft with limited or no true HOTAS particularly benefit: engine management, trim, radiators, flaps, gear and other frequently reached functions can share a convenient page. Keep tasks the user already handles comfortably on physical controls out of the way unless requested.
- Retain useful relationships such as keypad/display/line-select keys, radio controls and aircraft systems without requiring their original cockpit positions. Match a line-select button to its corresponding display row. Keep frequent operations together and put specialist tasks on a clearly linked page with consistent navigation rather than crowding everything onto one screen. Do not infer physical usability from a grid count or from the fact that the author calls it a tablet layout.
- Use screen space for operational controls and readable displays before decorative headings. Square keypad/function keys, taller channel displays and larger rotary gesture areas may justify changing cockpit proportions. Match control-owned artwork to the chosen bounds, cropping excess padding where appropriate rather than distorting the face. Treat the user's refinements as design evidence, not fixed dimensions to apply to other devices.
- Choose discrete switches or named direct-selection buttons according to the task. A radar option or countermeasure preset can benefit from a one-tap choice with actual-state highlighting. A switch plus neighboring direct-choice buttons can also be intentional. Inspect events before removing an apparent label: text beside a switch may itself be a working shortcut. Avoid adding duplicate commands for one gesture.
- Choose display composition by interaction: one control can combine several fields within a shared bezel; separately framed rows can each have their own binding and matching selection keys. Preserve meaningful spaces, line breaks and cue/status characters. Include every secondary telemetry variable used by a transform in the export checklist. Verify any separately configured calculated variables and optional fonts rather than assuming the deck import installs them.
- Inspect the input path per control. A DBMM deck can use DCS-BIOS feedback with keyboard input for some functions. Verify those shortcuts against the user's assignments; feedback does not prove that the input is portable. If one event sends both a keyboard action and a DCS command, establish whether they are complementary or duplicate the operation before copying that pattern.
- For a layout-only revision, compare control identities, event-to-command mappings, calculated command functions, feedback bindings and secondary dependencies against the baseline. Structural validation establishes neither unchanged behavior nor live cockpit acceptance. Classify older unknown switch events: empty extra entries may be serialization residue, while action-bearing entries require target-version review. Never apply a blanket index shift or discard working behavior merely to silence validation.

## Required deck description

Every deck that uses DCS-BIOS through DBMM must include the following user-facing installation notice in its `Description`:

```text
DBMM installation with DCS-BIOS is required
DBMM: https://github.com/tgudelj/DCS-BIOS-MATRIC-Middleware/releases
DCS-BIOS: https://github.com/DCS-Skunkworks/dcs-bios/releases/
```

Keep this notice with the deck's plain-language purpose and intended device information. It tells the importer which two components to obtain; detailed aircraft configuration belongs in the linked setup material.

## Inspect the installed definitions

Run these commands relative to the installed skill directory, replacing the example path with the user's actual location:

```powershell
python scripts/dcs_bios.py inventory "C:/path/to/DCS-BIOS/doc/json"
python scripts/dcs_bios.py inventory "C:/path/to/DCS-BIOS/doc/json" --aircraft F-16C_50 --search ICP
python scripts/dcs_bios.py inventory "C:/path/to/DCS-BIOS/doc/json" --aircraft F-16C_50 --control ICP_ENTR_BTN
python scripts/dcs_bios.py inventory "C:/path/to/DCS-BIOS/doc/json/F-16C_50.json" --control ICP_HUD_BRT_KNB
```

With a directory and no aircraft, the helper lists available modules and `AircraftAliases.json`. An aircraft name resolves to the modules listed in that installed alias map. A direct module JSON selects that module explicitly. CommonData and MetadataStart/MetadataEnd definitions are included when present. Identifiers shared by modules are ambiguous; inventory can select `--module`, while the audit refuses to guess. The helper records definition hashes for reproducibility and reads JSON only; it never executes Lua/JSONP or contacts DCS.

Each definition describes `inputs` and `outputs` independently. An output-only gauge or light is not automatically a valid command. Input forms include:

| Advertised interface | Command argument |
| --- | --- |
| `set_state` | Integer `0..max_value`, with meaning from the aircraft reference |
| `fixed_step` | `INC` or `DEC` |
| `variable_step` | Signed increment such as `+3200` or `-3200`, within its range |
| `action` | The exact advertised `argument`, for example `TOGGLE` when present |
| `set_string` | One-line text; consult the control reference for frequency/text formatting |

A familiar identifier or `TOGGLE` token is not proof of support. The helper checks the selected definition, but cannot validate the domain-specific content of every string input. A missing definition, unsupported interface or output ambiguity needs resolution, not a fabricated mapping.

## Commands from MATRIC to DCS

DBMM subscribes to MATRIC's **`DCS_INPUT_COMMAND`** string variable. When nonempty, it sends that text with a trailing newline to DCS-BIOS, then clears the variable. A deck writes one `IDENTIFIER ARGUMENT` command, without adding a newline or bundling several commands into the mailbox. It uses native **`ActionSetServerVariable`**, not a keyboard shortcut or an HTTP action.

The serialized action type is `EXM.MatricPro.Actions.ActionSetServerVariable` (singular). MATRIC's internal metadata ID is plural; the catalog and helper distinguish these. `action("ActionSetServerVariable", ...)` produces the correct JSON. The older helper lookup spelling `ActionSetServerVariables` remains an alias.

In a Python authoring script using the helper modules:

```python
from dcs_bios import load_definitions, find_control, command_action, feedback, ensure_mailbox

catalog = load_definitions("C:/path/to/DCS-BIOS/doc/json", "F-16C_50")
enter = find_control(catalog, "ICP_ENTR_BTN")
button["ControlEvents"] = [
    {"Name": "press", "Actions": [command_action(enter, 1)]},
    {"Name": "release", "Actions": [command_action(enter, 0)]},
]
ensure_mailbox(deck)
```

This snippet assumes a new `deck` and `button` created through `deck_tool.py` helpers. Inspect the definition before choosing 0/1: only use a press/release pair for a verified momentary control. Release-only shortcuts and held keyboard inputs have different semantics. Switches can use `position-increment`/`position-decrement` with verified absolute values or INC/DEC; if using specific transition events, take their exact names from the native catalog. Do not wire both the generic and specific events to duplicate the same command.

For exhaustive inventories, inspect raw definition metadata such as `api_variant: "momentary_last_position"` and the installed module implementation when necessary; the helper's normalized control record does not retain every source attribute. A name ending in `BTN` does not establish momentary behavior: some cockpit pushbuttons latch. A spring-return rocker may need two independently labeled buttons, each with its own press-to-end-state and release-to-center command, so copying one half remains functional. Keep maintained-state selectors distinct from those momentary pairs.

`ensure_mailbox` initializes `ReferencedUserVariables` with a persistent, user-editable STRING mailbox whose `Value` is empty and whose calculation is absent. For a new deck, never carry over a saved command such as `ICP_ENTR_BTN 0` from an example. Simulator feedback normally belongs to DBMM and should not be persisted as user-defined `dcs_` snapshots.

DBMM creates the runtime mailbox when it starts. The deck declaration does not register a live variable by itself. In the inspected MATRIC importer, `ReferencedUserVariables` is preserved as metadata without installing calculated user-variable definitions. Create any such variables explicitly in MATRIC's Variables dialog and document them with the deck, or combine outputs directly in a binding transform when possible. Do not promise that importing a deck alone sets up its calculations.

The mailbox is shared and is not an acknowledged command queue. Rapid repeated changes or command batches need live timing checks; do not claim guaranteed delivery or fix them by concatenating commands. Test that momentary inputs release and that the observed cockpit state matches the requested command.

## Feedback from DCS to MATRIC

DBMM publishes each output as **`dcs_<identifier>`**, preserving identifier case. `_ACFT_NAME` therefore becomes `dcs__ACFT_NAME`. Its listener decodes packed integer fields and strings; do not apply the bit mask/shift again in MATRIC. Integer outputs may still be normalized raw positions rather than physical units. Use the output range and aircraft reference for display scaling.

Native `Config.ControlBindings` entries contain `PropertyPath`, `VariableName` and optional `Transform`. The transform is a JavaScript function body receiving `(value, variables)`, with `variables` mapping names directly to values, without a `.Value` suffix.

| Intended display | Binding path | Example transform |
| --- | --- | --- |
| Button lamp/active appearance | `state.pressed` | `return Number(value) === 1;` for a verified 0/1 output |
| Native switch position | `state.position` | Empty for matching indices, otherwise explicit remapping |
| Slider/rotary percentage | `state.value` | `return Math.round(Number(value) * 100 / 65535);` for that output range |
| Display text | `Text` | `return String(value || '').replace(/\u0000/g, '');` for a string output |

Use a native MCButton with no actions as a simple text display. There is no `MCLabel` in the current native catalog. Labels, colors, images and scaling must reflect the chosen control's real configuration and intended meaning.

For an absolute native slider/rotary input, `scaled_action(control_definition)` generates a calculated mailbox command from `eventData.value` in 0..100 to its verified `set_state` maximum. Use the inverse range for feedback. Set `SendValueAfterInteractionEnd: true` when appropriate for feedback-bound controls, and verify interaction behavior live. This is native DCS integration, separate from excluded Stream Deck continuous slider mappings.

Calculated user variables can combine outputs, for example several display lines. Add every referenced `dcs_` output to DBMM's selection, and give derived variables distinct names to avoid collisions with other decks. Expressions should handle unavailable values and preserve meaningful whitespace. Do not copy captured simulator state from someone else's deck.

## Audit, export requirements and package

```powershell
python scripts/dcs_bios.py check /path/to/staged-deck --definitions "C:/path/to/DCS-BIOS/doc/json" --aircraft F-16C_50 --output /path/to/dcs-check.json
python scripts/deck_tool.py pack /path/to/staged-deck --output /path/to/MyCockpit.deck
```

The audit combines native deck validation with literal command checks, mailbox initialization and known telemetry identifiers. It extracts literal `variables['dcs_NAME']` dependencies from transforms and calculations, and reports `required_outputs_by_module` using unprefixed DCS-BIOS identifiers. That report is an authoring checklist, not a ready-to-import DBMM filter file. It does not evaluate JavaScript or prove dynamic command arguments, dynamic variable names, aircraft semantics or live feedback. Review its warnings.

If the panel uses a custom applet, supply its folder or `.mapl` with repeatable `--applet` arguments. This enables manifest event/parameter checks and includes applet `variable` parameter values/defaults in the dependency audit. Applet JavaScript can access additional variables that this static check cannot infer; include those in the DBMM output checklist explicitly. See [custom applets](custom-applets.md).

In DBMM, select the needed outputs for the detected aircraft and any applicable common/metadata modules, then use **File Ã¢â€ â€™ Export variables list** to produce a companion configuration. Users can apply it with **File Ã¢â€ â€™ Import variables list**, which merges the entries. Verify the selected outputs after import and restart/restart listening as needed for the installed build. This companion file is separate from `.deck` packaging.

Aircraft aliases and additional component modules need particular care: the installed DCS-BIOS alias map and DBMM's filter-module selection are not interchangeable. The inspected DBMM implementation combines the selected aircraft's list with CommonData and metadata lists; do not assume all aliased modules' filters are combined. Its variable names also ignore output suffixes, so controls with multiple outputs need middleware-specific verification. The helper refuses to automatically build such a feedback binding.

For an entirely synthetic example:

```text
python scripts/dcs_bios.py example --output /path/to/dcs-training
python scripts/dcs_bios.py check /path/to/dcs-training --definitions assets/dcs-demo/SKILL_DEMO.json
```

The `SYN_` definitions are original training fixtures and do not control a real aircraft. They demonstrate a momentary button, lamp feedback, a two-position switch, a scaled slider and string display. Generate a real panel from installed aircraft definitions before asking the user to validate it in DCS.

Legacy DBMM decks can mix keyboard shortcuts, custom applets and variable-based controls. Some inspected decks use older switch event names that differ from the current catalog. Their DBMM suffix is a useful discovery hint, not proof that every control is mapped or that the whole deck validates against a newer MATRIC build. Preserve existing behavior until the target version and conversion are verified.

## Evidence and live acceptance

The implementation was checked against the [DBMM translator](https://github.com/tgudelj/DCS-BIOS-MATRIC-Middleware/blob/970a393c384a268021af8cffb3780b520c7f48d4/DCSMATRICFeeder/MatricDCSTranslator.cs), its configuration/listener/send code, local DBMM decks for several aircraft, and installed DCS-BIOS definition JSON. No user deck or aircraft module implementation is distributed in this skill. The [DCS-BIOS protocol's alias generation](https://github.com/DCS-Skunkworks/dcs-bios/blob/main/Scripts/DCS-BIOS/lib/Protocol.lua) explains the aircraft-to-module map. Linked videos provide user context; their contents were not relied on for exact API claims.

Deliver the `.deck`, editable sources and required-output checklist, plus any verified DBMM companion filter. Ask the user to validate the correct aircraft/seat, command directions, momentary release, feedback after changing the cockpit directly, display formatting, and slider endpoints. State which checks were offline/native-import checks and which were actually performed with DCS running. Do not claim live compatibility from static validation alone.
