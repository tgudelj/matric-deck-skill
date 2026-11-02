# Farming Simulator input configuration

Use the [shared application input workflow](../application-inputs.md) for discovery, inventory, MATRIC mapping and acceptance. This reference covers application-specific formats and limits.


Inspect the selected edition's Documents/My Games/FarmingSimulator*/inputBinding.xml. Use the user's actual edition folder (for example FarmingSimulator2022 or FarmingSimulator2025), rather than selecting the newest file across editions. The reader supports the readable `inputBinding` / `actionBinding` / `binding` XML subset; inspect unfamiliar older/newer schemas before claiming coverage.

Reports preserve exact action names, device IDs, alternative binding indices, input tokens and binding attributes, including axisComponent, inputComponent and neutralInput. The full XML is retained in profile metadata. For `KB_MOUSE_DEFAULT`, known keyboard tokens and modifier chords can produce hotkey candidates. Mouse tokens and unknown keys remain unresolved. Controller inputs require an explicit confirmed vJoy map keyed by the exact reported device and single raw token; physical hardware IDs do not establish virtual-device correspondence. Axis signs, ranges, neutral values and action semantics require review even when a candidate exists. Mods may add actions unavailable without that mod loaded.

Format evidence: [GIANTS Binding API](https://gdn.giants-software.com/documentation_print.php?category=70&class=7278&version=engine), including XML binding attributes and modifier ordering. This documentation is not evidence of a user's current edition or mod configuration.
