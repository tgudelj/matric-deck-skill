# Euro Truck Simulator 2 input configuration

Use the [shared application input workflow](../application-inputs.md) for discovery, inventory, MATRIC mapping and acceptance. This reference covers application-specific formats and limits.


Inspect `controls.sii` within the selected user profile. Common roots are Documents/Euro Truck Simulator 2/profiles and steam_profiles, including redirected Documents folders. Confirm the actual current profile; backups and Steam copies may be stale. This addition targets ETS2, not the original Euro Truck Simulator or an unverified edition.

The reader accepts readable `SiiNunit` text, preserves the full configuration and inventories `config_lines[...]` mix expressions under exact mix names. Only a single `keyboard.<token>?0` expression can produce a known keyboard candidate. Alternatives, controller references, aliases, arithmetic, conditions, toggles, modifiers and timing expressions remain manual. They must not be collapsed into taps or treated as independent alternative inputs without understanding the expression. The helper does not evaluate SCS expressions, resolve device aliases or decrypt binary/encrypted saves. Unknown keys remain unresolved.

Format evidence: [SCS advanced input configuration](https://modding.scssoft.com/wiki/Documentation/Engine/Advanced_input_configuration). This describes saved mixes and device/input aliases, not proof of active profile selection.
