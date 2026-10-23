# Native action recipes

Use `deck_tool.py catalog --action <implementation-class-short-name>` to get the exact current template and property types. In Python, `action("ActionHotkey", KeyCode=67, Keystroke="C", Modifiers=["LCONTROL"])` returns a fresh configuration based on that template. Helpers never press a key or run an action.

## Buttons, held keys and macros

For a one-shot keyboard shortcut, place ActionHotkey on the button's `release` event. For a held input, place it on `press` and leave `release` without a duplicate shortcut; MATRIC synthesizes the implicit release. Adding the same shortcut to both events is not a generic requirement and can cause an extra activation. Keep `Toggle: false` unless a latched key is explicitly wanted.

Use Windows virtual-key `KeyCode` values, not ASCII for arbitrary characters. ASCII uppercase A-Z and digits happen to share their Windows VK values; that is not true for arbitrary punctuation or keyboard layouts. Known modifier names include `LCONTROL`, `RCONTROL`, `LSHIFT`, `RSHIFT`, `LALT`, `RALTGRAPH`, `LWIN`, `RWIN`. The catalog's top-level `key_codes` map comes from MATRIC's own input mapping. Do not use unrecognized `CTRL` or `ALT` aliases. Respect the user's keyboard layout.

ActionMacro uses `Items` with `EventType` values `"keydown"` and `"keyup"`, a `KeyCode`, optional display `Key`, and `Delay` in milliseconds. Balance keys/modifiers and verify timings against the implementation when a precise sequence matters. A sequence of actions can also include ActionDelay (`Delay` in milliseconds). Do not guess application-specific shortcuts from a label such as "Arm weapon".

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
