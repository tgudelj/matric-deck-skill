# Assetto Corsa Competizione input configuration

Use the [shared application input workflow](../application-inputs.md) for discovery, inventory, MATRIC mapping and acceptance. This reference covers application-specific formats and limits.


Inspect Documents/Assetto Corsa Competizione/Config/controls.json and explicitly selected saved JSON presets in Customs/Controls. Discovery checks JSON content for known input sections; unrelated JSON is excluded. Confirm the active preset and input mode in-game. This is ACC discovery, not Assetto Corsa or Assetto Corsa EVO support.

The reader preserves the full JSON, including axes, ranges, force-feedback settings, device declarations and unknown extensions. It inventories `uICommandButtonList` and `raceCommandButtonList`, retaining contexts, entry settings and separate instant, extended and pinkie action codes. Known `keyboardSettings` actionType/key chords can produce hotkey candidates. `bCmd`, unknown keys and non-keyboard records remain unresolved. Wheel/gamepad tokens use a report location rather than an inferred hardware identity. Long-press duration, pinkie dependencies and controller assignments require manual review; the helper does not emit a tap or infer vJoy correspondence for them. Axis configuration is retained as metadata rather than translated automatically.

Schema evidence is the original configuration example in [ACC controls.json discussion](https://steamcommunity.com/app/805550/discussions/0/2646360117223783712/), not a vendor-supported schema guarantee. Inspect the user's file when fields differ; saved paths, Unreal key names and numeric controller indices must not be assumed interchangeable with MATRIC/Windows inputs.
