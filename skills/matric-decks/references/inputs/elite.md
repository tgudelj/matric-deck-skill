# Elite Dangerous input configuration

Use the [shared application input workflow](../application-inputs.md) for discovery, inventory, MATRIC mapping and acceptance. This reference covers application-specific formats and limits.

Start at `%LOCALAPPDATA%/Frontier Developments/Elite Dangerous/Options/Bindings`. Inspect `StartPreset*.start` and confirm the corresponding selected `.binds` files and version in-game, including multiple section presets. If the active stock preset is absent from this user folder, inspect that exact preset under the installed game's `ControlSchemes`. The reader handles `Root PresetName`, primary/secondary alternatives, axis `Binding`, keyboard/joystick modifiers and hold/toggle/inversion/deadzone settings. Device identifiers can be names or hardware IDs; never infer that an arbitrary `Joy_1` is MATRIC's device. [EDCD device identity guidance](https://github.com/EDCD/EliteCustomButtonNames/).

Confirm selected presets for each needed section: ship, SRV, on-foot and general.

Format evidence also includes [SpaceSimControlManager](https://github.com/philchuang/spacesimcontrolmanager).
