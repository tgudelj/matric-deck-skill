# Flight and space simulator input decks

Use this workflow for Microsoft Flight Simulator 2020/2024, Star Citizen and Elite Dangerous on Windows PC. Scope is input through native MATRIC keyboard and embedded vJoy actions. It does not implement SimConnect, telemetry, journals or other state feedback. Older Flight Simulator editions need separate format evidence before claiming support.

## Choose useful auxiliary controls

Build a companion to the user's existing flight controls. Unless explicitly requested, leave primary flight-stick pitch/roll/yaw and continuous maneuvering to their physical controls. Good deck candidates are throttle/speed presets or sliders, flaps, spoilers, landing gear, trim steps, mixture, propeller pitch, radiator/cowl flaps, lights, autopilot, cameras and communications. Space-sim candidates include power allocation, targeting, travel/docking modes, speed limiter, mining/salvage controls and ship systems. These are design suggestions, not promises that a given aircraft/ship/version exposes every action.

Use native sliders/absolute rotaries for confirmed analogue axes; encoders for verified increase/decrease actions; momentary buttons for taps/holds; multi-position switches only for actual discrete set-state inputs. A game toggle binding supports a toggle command, not a trustworthy ON/OFF indicator. Local slider/switch values show what the user last sent and can differ from the game after other input, respawn, aircraft changes or reconnects. Avoid unsolicited startup axis writes. Check throttle direction, reverse/idle ranges, aircraft-specific behavior and conflicts with a physical throttle before delivery.

Confirm the game build/edition, keyboard layout, selected profile(s), aircraft/ship and device correspondence. For MSFS 2024 this includes general, category and aircraft profiles. For Elite include the controls sections the user needs (ship, SRV, on-foot, general); they can select different presets. For Star Citizen confirm the installation channel (LIVE/PTU/etc.) and current export. Keep file discovery read-only and restricted to the user's relevant game/settings folders.

## Discover and inventory

Run relative to the installed skill directory:

```text
python scripts/game_bindings.py discover --game elite --root /path/to/Bindings --output /path/to/candidates.json
python scripts/game_bindings.py inventory --game elite --profile /path/to/Selected.4.2.binds --require-action LandingGearToggle --output /path/to/bindings.json
python scripts/game_bindings.py inventory --game starcitizen --profile /path/to/layout_mycontrols_exported.xml --output /path/to/bindings.json
python scripts/game_bindings.py inventory --game msfs2024 --profile /path/to/general-inputprofile --profile /path/to/aircraft-inputprofile --output /path/to/bindings.json
```

Game choices are `msfs2020`, `msfs2024`, `starcitizen`, `elite`. Discovery lists candidates and Elite `StartPreset*.start` selections; it never chooses the newest file or changes the active profile. Inventory accepts repeated explicit `--profile` selections without merging them or inventing precedence. Use `--active-confirmed` only after actual selection was established from the user or game UI; the flag records that evidence, it does not discover it. Profile XML cannot by itself establish active selection. Never change a user's mappings to make a generated deck appear complete.

Reports contain exact action/context identifiers, primary/secondary/rebind slots, raw input tokens, modifier devices, nested settings, profile metadata, SHA-256 hashes and modification times. `candidate` is a native action configuration for review, not an executable test or complete control/event binding. Known keyboard tokens produce `ActionHotkey`; unknown punctuation/layout-dependent keys, unfamiliar chords and mixed-device modifiers remain unresolved. MSFS keyboard numeric keys are interpreted only when the profile device is explicitly `Keyboard`; joystick numbers are not Windows key codes.

Check `missing_actions`, per-binding warnings and possible shared-input conflicts before authoring. `--require-action` takes exact action identifiers, not English labels; a missing result means no explicit bound entry in the supplied files, not proof that the game has no default. Conflict checks cover identical inputs in the same context among supplied profiles, including translated candidates, but cannot prove all overlapping contexts, aliases, profile precedence or timing-sensitive combinations. Read preserved flags, activation modes and axis settings. The helper never infers how many milliseconds a hold needs or emits a double tap automatically. Build and explain any needed macro only from verified semantics.

### Game file sources and limits

- **Star Citizen:** Prefer a fresh export through Options > Keybindings > Advanced Controls Customization > Control Profiles > Save Control Settings. RSI documents `layout_<name>_exported.xml` beneath `<installation>/<channel>/USER/Client/0/Controls/Mappings`. Installed `actionmaps.xml` can also contain explicit overrides. The reader supports `ActionMaps`/`ActionProfiles`, `actionmap`/`action`/`rebind`, device options, explicit clears such as `js1_ `, and retains multi-tap/activation attributes. Exports/overrides may omit unchanged defaults and their activation definitions. For an omitted requested action, inspect matching-build installed defaults or verify the binding in-game; do not substitute remembered default keys. Default-profile merging and `Data.p4k` extraction are not implemented. [Official profile instructions](https://support.robertsspaceindustries.com/hc/en-us/articles/360000183328-Create-export-and-import-custom-profiles).
- **Elite Dangerous:** Start at `%LOCALAPPDATA%/Frontier Developments/Elite Dangerous/Options/Bindings`. Inspect `StartPreset*.start` and confirm the corresponding selected `.binds` files and version in-game, including multiple section presets. If the active stock preset is absent from this user folder, inspect that exact preset under the installed game's `ControlSchemes`. The reader handles `Root PresetName`, primary/secondary alternatives, axis `Binding`, keyboard/joystick modifiers and hold/toggle/inversion/deadzone settings. Device identifiers can be names or hardware IDs; never infer that an arbitrary `Joy_1` is MATRIC's device. [EDCD device identity guidance](https://github.com/EDCD/EliteCustomButtonNames/).
- **MSFS 2020/2024:** Inspect the chosen account/store's readable profile files. Steam installations commonly use `Steam/userdata/<account>/1250410/remote/inputprofile_*` (2020) or `2537590/remote/inputprofile_*` (2024). Store installations commonly keep readable XML blobs below `%LOCALAPPDATA%/Packages/Microsoft.FlightSimulator_8wekyb3d8bbwe/SystemAppData/wgs` (2020) or `Microsoft.Limitless_8wekyb3d8bbwe/SystemAppData/wgs` (2024). These are discovery hints, not a supported universal export API; use explicit local paths and avoid other account data. Readable XML may contain adjacent `Version`, `FriendlyName`, `Device` elements rather than one root. The reader also accepts wrapped XML and both `Action`/`Actions` entries. Preserve contexts, GUIDs, aircraft metadata, `Flag`, `ValueEvent`, `Delay`, key information and global/local axis curves. Binary/cloud containers, encrypted/unknown formats and automatic active-layer resolution are unsupported; if no readable mapping is available, obtain verified assignments through the game settings. Microsoft's SDK input XML documents device/action structures, but developer defaults are not evidence of a user's active mapping. [Input XML](https://docs.flightsimulator.com/msfs2024/retail/content-configuration/input/input-configuration-xml-properties/), [profile layers](https://flightsimulator.zendesk.com/hc/en-us/articles/16459737949980-Controller-Settings-FAQ), [FSProfiles format and location evidence](https://github.com/iadarroch/FSProfiles).

## Map the game's device to MATRIC vJoy

MATRIC supports virtual joystick input through vJoy. A physical HOTAS mapping can guide a design but its game device identity cannot be impersonated simply by copying its button number. Confirm the game sees the configured MATRIC/vJoy device. Use an existing binding on that device when available. Otherwise deliver an explicit list of game actions the user must bind to the proposed virtual inputs; label those controls as requiring setup. Never silently reassign physical controls or treat vJoy as Xbox/XInput emulation.

Obtain the actual vJoy DeviceId, configured buttons, axes and **discrete** POV count from the user's MATRIC device configuration. The driver must be installed/enabled and the device available to MATRIC. Device ordering can change in-game. Do not assume `js1`, a GUID or an Elite hardware ID equals vJoy DeviceId 1. No driver access is required for inventory.

An optional `--device-map /path/to/device-map.json` supplies explicitly verified correspondence. The top-level keys must match report `device` exactly (Star Citizen `js2`, MSFS GUID, Elite device identifier). `inputs` keys must match a single raw report input token. Multiple-input chords remain manual work. This deliberately avoids guessing each game's numbering, axis names or POV conventions:

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

## Delivery and acceptance

Create each native control from the catalog, reuse installed visual templates where suitable, and attach only reviewed action candidates. Size auxiliary controls for the intended phone/tablet. Deliver an importable deck plus a short mapping/setup table naming each game action, source profile/context, keyboard or virtual input, and any required rebinding. Deck descriptions should state the game/edition, purpose, target screen and whether virtual joystick setup is required. Do not add DBMM/DCS-BIOS or other feedback dependencies for these input-only decks.

Validate/package with `deck_tool.py` and audit the requested-action coverage. Test synthetic samples without operating the game. Actual acceptance belongs in the user's game with the intended profiles active: check taps and holds, release/cancellation, modifier behavior, axis direction/endpoints and reconnect/page changes. Distinguish file/catalog checks from that acceptance. Keep real mappings, account paths, profile reports and game assets out of this skill's distribution and public fixtures.

## Implementation evidence

The parser is original standard-library Python; no game dataset or third-party implementation is copied. Format behavior was checked against the official RSI and Microsoft documentation above, FSProfiles' `ControllerDefinition.cs`/profile readers, and the original [SpaceSimControlManager](https://github.com/philchuang/spacesimcontrolmanager) Elite mapping model and Star Citizen sample structure. These projects are format evidence rather than runtime dependencies. Synthetic tests cover the supported subset; unknown extensions and future game updates require inspection before claiming compatibility.
