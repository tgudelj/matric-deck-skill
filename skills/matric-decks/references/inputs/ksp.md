# Kerbal Space Program input configuration

Use the [shared application input workflow](../application-inputs.md) for common selection, mapping and acceptance guidance. Use `--game ksp` for the original desktop Kerbal Space Program (KSP 1). Read the selected installation's root `settings.cfg`, including the user's chosen Steam or standalone installation. Do not assume a different installation or remembered default bindings are active. This reader does not support KSP 2's InputBindings.json, mod-specific settings, craft action-group definitions or controller middleware profiles.

Run relative to the installed skill directory:

```text
python scripts/game_bindings.py discover --game ksp --root "/path/to/Kerbal Space Program"
python scripts/game_bindings.py inventory --game ksp --profile "/path/to/Kerbal Space Program/settings.cfg" --output /path/to/ksp-inputs.json
```

Discovery considers settings.cfg files and requires recognizable input nodes; mod settings without supported input bindings are excluded. Inventory accepts explicit renamed copies.

The standard-library reader supports line-based ConfigNode nodes, braces, key/value records and comments. It preserves the full raw text and parsed tree, including duplicate values, nested axis records and unknown settings. Malformed, excessively nested or unsupported inline syntax is rejected rather than silently repaired. Keyboard nodes expose primary/secondary alternatives; nested axis PRIMARY/SECONDARY entries retain device names, axis numbers, inv, sensitivity, deadzone, scale, group and modeMask. Legacy flat axis nodes with id fields are retained for manual review.

Known Unity key names, including Alpha0–Alpha9 and Keypad0–Keypad9, can produce Windows hotkey candidates. Unity enum integers must not be treated as Windows virtual-key codes. Unknown keys, punctuation and modifier-only assignments stay unresolved. A non-Any switchState disables automatic translation. Group and mode settings remain source data, not proof that all reported bindings share an active context; review possible conflicts accordingly. MODIFIER_KEY is inventoried independently and does not imply that a modifier chord should be added to other actions. Verify hold, toggle, staging, docking, editor and EVA behavior before choosing native control events.

Joystick button tokens retain Unity names such as Joystick1Button0. JoystickAny means an unspecified joystick, not a verified device. Axis inputs use report tokens such as `axis:2` under the exact saved device name. Only an explicit verified device/input map can produce vJoy candidates; never infer vJoy identity, one-based button numbers or HID axis usages from Unity indices. Review inversion, ranges, group and mode settings separately; candidates do not automatically reproduce sensitivity or deadzone curves. Legacy id axes remain manual. Local MATRIC state is not vessel feedback; no kRPC, serial bridge, telemetry or live KSP integration is implemented.

Evidence: generated KSP 1.12.4 API references for [GameSettings](https://kspmoddinglibs.github.io/KSPDocsSite/class_game_settings.html), [KeyBinding](https://kspmoddinglibs.github.io/KSPDocsSite/class_key_binding.html) and [AxisBinding](https://kspmoddinglibs.github.io/KSPDocsSite/class_axis_binding.html), the original [saved configuration example](https://github.com/jeffmcfadden/ksp/blob/master/settings.cfg), and the original [nested axis configuration report](https://steamcommunity.com/app/220200/discussions/0/2595630410177064451/). These establish the supported subset, not a vendor schema guarantee or active-user configuration. No third-party dataset or real settings file is distributed. Offline synthetic tests and packaging checks do not establish native import or live-game acceptance.
