# iRacing input configuration

Use the [shared application input workflow](../application-inputs.md) for discovery, inventory, MATRIC mapping and acceptance. This reference covers application-specific formats and limits.


Discovery lists `controls.cfg` below the explicit iRacing root, including car setup folders. Confirm whether global or custom controls for the current car are selected. Calibration in `joyCalib.yaml` is a separate file; the helper does not parse YAML or treat it as hotkey assignments. Do not reset or delete either file as part of discovery.

The reader supports the reverse-engineered GFCC version 20 / LRTC version 8 record layout only. It checks payload and record bounds and preserves raw record bodies, flags, type/value/modifier integers, GUID slots, global bytes and trailer bytes. Unknown versions fail explicitly. **Every translation stays manual**, including keyboard modifiers, button bitmasks and axis indices. The slots are reported without claiming a verified device identity; no physical-device or Windows-key conversion is inferred. Built-in defaults and active per-car precedence cannot be established from these records alone.

Evidence: [iRacing controller configuration locations](https://support.iracing.com/support/solutions/articles/31000133335-controller-setup-and-calibration) and the original [iracing-tracker GFCC codec](https://github.com/dillonkirsch/iracing-tracker/blob/master/src/irtracker/gfcc/codec.py). The latter is reverse-engineered format evidence, not an official API or an installed dependency. The helper contains an original bounded reader, not a copied codec or real configuration fixture.
