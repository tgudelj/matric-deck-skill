# Application input discovery and MATRIC mapping

Discover the inputs configured in the target application, then map reviewed keyboard or virtual-joystick inputs to MATRIC actions. Application genre does not change this workflow. The bundled standard-library helper supports the readers listed below; for other applications, research a discovery method as described below and obtain verified configuration/export evidence or user-confirmed assignments before authoring bindings. Do not invent a format or infer remembered default shortcuts.

This workflow provides input only. Native application integrations and telemetry/feedback are separate capabilities. A local control value records what MATRIC sent, not the application's actual state.

## Select the application and configuration

Confirm the application version/edition, selected installation/account/profile, keyboard layout, relevant task contexts and device correspondence. Restrict read-only discovery to the relevant settings folder. Do not choose the newest file as proof of active selection, change mappings, switch profiles, reset preferences or send inputs to discover assignments. Saved files can be stale; ask the user to save current settings through their normal workflow when necessary.

Read only the relevant format reference:

| Application | Helper selector | Configuration and limits |
| --- | --- | --- |
| Microsoft Flight Simulator 2020/2024 | `msfs2020`, `msfs2024` | [Readable input XML and profile layers](inputs/msfs.md) |
| X-Plane 11/12 | `xplane` | [Keyboard/joystick PRF files](inputs/xplane.md) |
| Star Citizen | `starcitizen` | [Explicit XML rebinds](inputs/starcitizen.md) |
| Elite Dangerous | `elite` | [BINDS files and section presets](inputs/elite.md) |
| Euro Truck Simulator 2 | `ets2` | [SII mix expressions](inputs/ets2.md) |
| Farming Simulator | `farmingsimulator` | [GIANTS inputBinding XML](inputs/farmingsimulator.md) |
| iRacing | `iracing` | [Experimental binary record inventory](inputs/iracing.md) |
| Assetto Corsa Competizione | `acc` | [Input JSON and timing](inputs/acc.md) |
| Kerbal Space Program 1 | `ksp` | [ConfigNode key/axis settings](inputs/ksp.md) |

## Applications without a recipe

If the target application has no input-discovery reference, research its configuration files, binding exports or read-only discovery interfaces using official documentation and internet search. Prefer documentation or implementation evidence for the user's edition/version; community examples can provide leads, but verify their format and meaning against the target application and relevant local files when available. Recipes establish known methods, not an exhaustive list of applications MATRIC can control.

Identify how to obtain the user's actual assignments, selected profile/context, modifiers, device identities and timing/axis settings. Published defaults establish possible shortcuts, not the user's active bindings. Record the discovery source and remaining uncertainties. A task-specific reader or inspection method may be used when supported by verified format evidence; the helper's existing --game choices do not automatically support a new application. Preserve unknown fields and keep discovery read-only. Research alone does not authorize installing software, editing configuration or operating controls.

If discovery remains unavailable after researching the relevant sources, or internet access is unavailable and local evidence is insufficient, explain the specific gap and request an export, configuration path or verified assignments. Continue independent layout work when useful; provide unresolved controls only when the user accepts an unfinished layout, and identify them clearly. Never fabricate bindings to complete a deck or describe an unverified method as tested.

## Discover and inventory

Run relative to the installed skill directory. The existing `game_bindings.py` name and `--game` selector are retained for compatibility; all readers use the same interface regardless of genre.

```text
python scripts/game_bindings.py discover --game elite --root /path/to/Bindings --output /path/to/candidates.json
python scripts/game_bindings.py inventory --game elite --profile /path/to/Selected.binds --require-action LandingGearToggle --output /path/to/bindings.json
```

Substitute the selector and paths from the relevant application reference. Inventory accepts repeated explicit `--profile` selections without merging precedence; application-specific restrictions still apply. `--active-confirmed` records selection already established with the user/application UI; it does not discover that selection. `--output` refuses to overwrite existing reports. Never change mappings to make a generated deck appear complete.

Reports preserve exact action/context identifiers, binding alternatives, raw tokens, modifiers, nested settings, metadata, source SHA-256 hashes and modification times. Inspect preserved raw configuration, warnings and unsupported/unparsed records before claiming coverage. `candidate` is a native MATRIC action configuration for review, not an executable test or complete control/event binding. Known keyboard tokens may produce ActionHotkey; unknown/layout-dependent keys, unfamiliar chords and unsupported timing remain unresolved. Numeric input enums, joystick indices and device IDs are not interchangeable with Windows key codes or vJoy targets.

Check `missing_actions` and possible shared-input conflicts. `--require-action` takes exact identifiers, not English labels. Missing means no explicit bound entry in the supplied files; it does not prove the application has no default. Conflict checks cover identical reported inputs in the same context, including translated candidates, but cannot establish every overlapping context, alias, profile layer or timing-sensitive combination.

## Map inputs to controls

Choose controls around the user's workflow and target screen. Preserve application action semantics, alternatives, modifiers, holds, repeats, releases and axis settings. Use native sliders/absolute rotaries for verified analogue axes, encoders for verified increase/decrease commands, momentary buttons for taps/holds and selectors for actual discrete set-state commands. A toggle shortcut does not establish an ON/OFF state indicator. Do not infer a hold duration, emit double taps automatically or send unsolicited startup axis values.

Use verified keyboard assignments directly. If an operation needs a macro or modifier handling that a candidate does not express, resolve its semantics before authoring it. Keep unsupported assignments visibly unresolved and disclose required rebinding. Match visual design to the requested application and hardware using the skill's separate appearance guidance; configuration discovery establishes behavior, not appearance.

## Map a virtual joystick

MATRIC supports virtual joystick input through vJoy. A physical controller mapping can guide a design but its application device identity cannot be impersonated simply by copying its button number. Confirm the application sees the configured MATRIC/vJoy device. Use an existing binding on that device when available. Otherwise deliver an explicit list of application actions the user must bind to the proposed virtual inputs; label those controls as requiring setup. Never silently reassign physical controls or treat vJoy as Xbox/XInput emulation.

Obtain the actual vJoy DeviceId, configured buttons, axes and **discrete** POV count from the user's MATRIC device configuration. The driver must be installed/enabled and the device available to MATRIC. Device ordering can change in the application. Do not assume `js1`, a GUID or an Elite hardware ID equals vJoy DeviceId 1. No driver access is required for inventory.

An optional `--device-map /path/to/device-map.json` supplies explicitly verified correspondence. The top-level keys must match report `device` exactly (Star Citizen `js2`, MSFS GUID, Elite device identifier, or X-Plane's `xplane-joystick` namespace after confirming each input). `inputs` keys must match a single raw report input token. Multiple-input chords remain manual work. This deliberately avoids guessing each application's numbering, axis names or POV conventions:

```json
{
  "js2": {
    "DeviceId": 1,
    "buttons": 32,
    "axes": [48, 49, 50, 53],
    "povs": 1,
    "inputs": {
      "button3": {"kind": "button", "button": 3},
      "z": {"kind": "axis", "axis": 50, "invert": false},
      "hat1_up": {"kind": "pov", "pov": 1, "direction": "N"}
    }
  }
}
```

This is a synthetic configuration example, not a claim about a user's device or a universal Star Citizen token. The helper checks targets against the supplied capabilities; it cannot establish their truth or driver availability. Only put a device in this map after confirming that it is the intended virtual device. Keyboard/other-device modifiers combined with joystick inputs remain manual work. Use [vJoy action recipes](action-recipes.md#virtual-joystick-input) to place candidates on compatible native control events.

## Deliver and verify

Create controls from the catalog, reuse suitable installed visual templates and attach reviewed action candidates to compatible events. Deliver the importable deck and editable source/assets with a short mapping/setup table naming each application action, source profile/context, keyboard or virtual input and required rebinding. Descriptions should state purpose, application/version, target screen and external setup requirements.

Validate/package with deck_tool.py and audit requested-action coverage. Keep deterministic structural/catalog checks separate from native import and live acceptance. Actual application acceptance checks the intended active profiles and contexts, taps/holds, release/cancellation, modifiers, axis direction/endpoints and reconnect/page changes. Review conflicts with physical controllers. Keep real mappings, credentials, account paths, reports and application assets outside the distributed skill and public fixtures.

The helpers are original standard-library Python; linked documentation and implementations are format evidence, not runtime dependencies or promises of future compatibility. Unknown extensions and application updates require inspection before claiming support.
