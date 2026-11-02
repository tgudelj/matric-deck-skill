# Star Citizen input configuration

Use the [shared application input workflow](../application-inputs.md) for discovery, inventory, MATRIC mapping and acceptance. This reference covers application-specific formats and limits.

Prefer a fresh export through Options > Keybindings > Advanced Controls Customization > Control Profiles > Save Control Settings. RSI documents `layout_<name>_exported.xml` beneath `<installation>/<channel>/USER/Client/0/Controls/Mappings`. Installed `actionmaps.xml` can also contain explicit overrides. The reader supports `ActionMaps`/`ActionProfiles`, `actionmap`/`action`/`rebind`, device options, explicit clears such as `js1_ `, and retains multi-tap/activation attributes. Exports/overrides may omit unchanged defaults and their activation definitions. For an omitted requested action, inspect matching-build installed defaults or verify the binding in-game; do not substitute remembered default keys. Default-profile merging and `Data.p4k` extraction are not implemented. [Official profile instructions](https://support.robertsspaceindustries.com/hc/en-us/articles/360000183328-Create-export-and-import-custom-profiles).

Confirm the installation channel (LIVE/PTU/etc.) and current export.

Format evidence also includes [SpaceSimControlManager](https://github.com/philchuang/spacesimcontrolmanager).
