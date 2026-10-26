# Native action recipes

Use `deck_tool.py catalog --action <implementation-class-short-name>` to get the exact current template and property types. In Python, `action("ActionHotkey", KeyCode=67, Keystroke="C", Modifiers=["LCONTROL"])` returns a fresh configuration based on that template. Helpers never press a key or run an action.

## Buttons, held keys and macros

For a one-shot keyboard shortcut, place ActionHotkey on the button's `release` event. For a held input, place it on `press` and leave `release` without a duplicate shortcut; MATRIC synthesizes the implicit release. Adding the same shortcut to both events is not a generic requirement and can cause an extra activation. Keep `Toggle: false` unless a latched key is explicitly wanted.

Use Windows virtual-key `KeyCode` values, not ASCII for arbitrary characters. ASCII uppercase A-Z and digits happen to share their Windows VK values; that is not true for arbitrary punctuation or keyboard layouts. Known modifier names include `LCONTROL`, `RCONTROL`, `LSHIFT`, `RSHIFT`, `LALT`, `RALTGRAPH`, `LWIN`, `RWIN`. The catalog's top-level `key_codes` map comes from MATRIC's own input mapping. Do not use unrecognized `CTRL` or `ALT` aliases. Respect the user's keyboard layout.

ActionMacro uses `Items` with `EventType` values `"keydown"` and `"keyup"`, a `KeyCode`, optional display `Key`, and `Delay` in milliseconds. Balance keys/modifiers and verify timings against the implementation when a precise sequence matters. A sequence of actions can also include ActionDelay (`Delay` in milliseconds). Do not guess application-specific shortcuts from a label such as "Arm weapon".

## Native selectors and rotary controls

Use native multi-position switches for finite selectors when the target's states and touch interaction fit. Named direct-selection buttons can be preferable for immediately choosing a radar setting, countermeasure program or preset without stepping through intermediate positions. Give each button a verified set-state command. When feedback is available, bind each button's active appearance to the same actual-state variable with the appropriate value comparison so the group reflects external changes; a separate local toggle cannot establish actual state. For a switch, `MCThreePositionSwitch` uses `MCMultiPositionSwitchConfig`, with `DefaultValue`, `SwitchOrientation` (`horizontal`, `vertical` or `automatic`) and one `SwitchStateImages` entry per zero-based position. Put the state artwork and position labels in those control-owned images. Choose a default as an initial display only; use verified `state.position` feedback to reflect actual application/simulator state.

The inspected client increments on the right half of a horizontal switch or the top half of a vertical switch; the other half decrements, stopping at the endpoints. Visual order and target state values may therefore need an explicit mapping, with the inverse applied to feedback. Do not assume a cockpit label such as `1` is native index 1.

For three positions, specific events are `positionchange-0-1`, `positionchange-1-0`, `positionchange-1-2` and `positionchange-2-1`. Absolute commands on those events can set the verified target state. The client also emits `position-increment`/`position-decrement` for the same changes: bind either generic events or specific transitions, not both to duplicate a command. Check the selected control's catalog for its exact event set.

For relative turning, `MCRotaryEncoder` exposes `clockwise` and `counterclockwise`; a native action on each event can send one verified increment/decrement. Set a positive `Ticks` value, provide `DialImage`/`DialImageActive` with a visible `DialSize`, and set `ButtonSize: 0` if no center-button interaction is wanted. A painted knob on the page background is not interactive. Encoder angle follows local interaction and is not automatically an absolute target-state indicator. Use `MCRotary` or `MCSlider` when the task instead needs a verified absolute value mapping.

## Virtual joystick input

MATRIC's native vJoy actions support buttons, axes and discrete POVs. Use the game's actual input mapping plus confirmed virtual-device capabilities. vJoy provides joystick input, not Xbox/XInput identity or simulator state feedback. A physical joystick's device identifier cannot be replaced by matching its button number alone; confirm or explicitly plan the game's vJoy bindings. For MSFS, Star Citizen and Elite Dangerous, read [game inputs](game-inputs.md).

- `action("ActionVjoyButton", DeviceId=<confirmed-id>, ButtonId=<confirmed-button>)` belongs on `press` for a held button or a compatible discrete event for a pulse. It requires implicit release; follow the catalog event contract rather than adding a second activation on release. The runtime forwards ButtonId to vJoy's SetBtn.
- `action("ActionVJoyAxis", DeviceId=<confirmed-id>, Axis=50, InvertAxis=False)` belongs on a native `MCSlider`'s `valuechange`. Axis is a numeric HID usage: X/Y/Z = 48/49/50, RX/RY/RZ = 51/52/53, sliders = 54/55. Use only axes actually configured on that device. The inspected action consumes integer `value` as 0..100 percent and optionally computes `100 - value`; do not supply raw driver axis values. `AutoReset: false` is appropriate for a throttle/mixture lever whose requested position should remain after releasing the screen. A two-axis stick action is also in the catalog but primary flight-stick layouts are not a default recommendation.
- `action("ActionVJoySetAxisValue", DeviceId=<confirmed-id>, Axis=50, Value=50)` sends a fixed percentage on a compatible discrete event, useful for confirmed throttle detents/presets. Value is 0..100, not raw HID range. This action sets a value rather than incrementing it; an encoder needs verified increase/decrease inputs or an explicitly designed local value calculation.
- `action("ActionVjoyPOV", DeviceId=<confirmed-id>, POVId=<confirmed-hat>, POVDirection="N")` uses the strings `N`, `E`, `S`, `W`, `NONE`. It requires implicit release to return to neutral. The inspected runtime uses discrete POV input; continuous hats and diagonal directions are not supported by this action.

Use explicit runtime button/hat IDs verified for the target. The inspected manager forwards these IDs unchanged to vJoy; upstream vJoy's API uses one-based button/hat targets, whereas the inspected editor's button/POV lists enumerate from zero. The game-input helper validates one-based API targets against supplied counts; do not derive them from the editor's list position or assume this discrepancy is resolved in all builds. Verify execution on the target before claiming live button/POV support. [Upstream vJoy API example](https://github.com/shauleiz/vJoy/blob/master/SDK/c%23/FeederDemoCS/Program.cs).

Axis inversion in the game and MATRIC compose: preserve the profile's inversion/curves for review, and choose the MATRIC direction deliberately rather than automatically applying an inverse twice. Labels showing throttle/flap percentages or a toggle's last input must not imply live game feedback. Confirm focus and input release in the user's actual setup; structural deck validation does not operate a driver.

## Navigation and text

ActionGoToPage uses `TargetPageId` and is suitable for a button's `release`. ActionLoadDeck targets another deck and adds an external dependency; inspect its template rather than reusing page navigation fields.

ActionText uses `TextValue`, `TypeAsText`, and `SendToClipboard`. The starter uses TypeAsText=true and SendToClipboard=false. Text is input into the focused application when the user activates the control. Merely importing a package does not type it.

## OBS Studio

Read obs-discovery.md first when actual collection/scene/source names are needed. Native MATRIC action names differ from obs-websocket request names:

- ActionOBS with `Command: "SetCurrentScene"`, `Collection: <exact saved collection name>` and `Scene: <exact scene name>`.
- ActionOBS with `Command: "SetPreviewScene"` for preview selection, when Studio Mode is applicable.
- ActionOBS with `Command: "StartStopRecording"`, `"StartStopStreaming"`, `"ReplayBufferSave"`, or `"ToggleStudioMode"` for those operations.
- ActionOBS with `Command: "SourceShow"`, `"SourceHide"` or `"SourceToggle"`, plus the appropriate `Scene` and `Source` names for visibility. Groups and repeated scene-item instances can require special handling; a name-only native action cannot express every scene-item-ID distinction.
- ActionOBS with `Command: "ToggleAudioInput"` and `Source: <audio input name>` for audio mute. This is different from hiding a scene item.
- ActionOBSVolume with its catalog defaults, `Command: "SetVolume"`, and the exact `Source` on a slider's `valuechange` event. Keep `SendValueAfterInteractionEnd: true` for a feedback-bound native slider unless the user chooses another interaction policy.

Names in a collection export prove saved configuration, not that a running OBS connection is available. The user must configure MATRIC's native OBS integration to execute native OBS actions later. Offline discovery does not require that connection. No credentials belong in deck JSON.

## Windows audio and other integrations

ActionMixerMute's enum strings include `"mute"`, `"unmute"`, `"toggle"`; audio Direction includes `"Capture"` and `"Render"`. ActionMixerVolume is a native slider action. Actual DeviceId and optional application path/title should come from the user's setup or an existing exported configuration. Do not fabricate a default-device ID or infer a current session ID from an application label.

Run/focus application, HTTP, virtual joystick and other native actions are available in the catalog. Read the matching template and verify the target path, URL, device/driver requirements or action-specific values. Structural validation cannot establish that those external targets exist. For a deck intended to be portable, state those dependencies explicitly.

## Experimental Stream Deck plugins

Do not invent plugin UUIDs, action UUIDs, opaque settings, controller values or resource declarations. Reuse a tested binding supplied by the user or configure it through the plugin's inspector. Preserve opaque settings when editing an existing deck. A fresh occurrence needs its own StreamDeckInstanceId, but changing that ID without remapping plugin-owned resources is insufficient for cloning a resource-bearing action. Plugin installers and global settings are not bundled by the offline helper. Keep the currently documented compatibility exclusions.
