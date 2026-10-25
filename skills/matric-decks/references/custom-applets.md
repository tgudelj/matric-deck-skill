# Custom applet authoring

Use this advanced path when native controls cannot satisfactorily express the requested interaction or display. A custom applet is an HTML/CSS/JavaScript interface inside one `MCCustom` iframe. Good candidates include a touch-selectable history graph, a specialized instrument or an interactive map. A different-looking button, slider or rotary normally needs native control artwork rather than an applet.

## Author and deliver

Run the standard-library helpers from the installed skill directory:

```text
python scripts/applet_tool.py new --id my-history-inspector --title "History inspector" --output /path/to/applet
python scripts/applet_tool.py validate /path/to/applet
python scripts/applet_tool.py pack /path/to/applet --output /path/to/History.mapl
python scripts/deck_tool.py validate /path/to/deck --applet /path/to/History.mapl
python scripts/deck_tool.py pack /path/to/deck --applet /path/to/History.mapl --output /path/to/History.deck
```

`new` supplies an original history inspector with a small bridge and no external libraries. Customize its interface, parameters, event payloads and actions for the task. Give a separate applet a fresh explicit ID; reuse an ID only for an intended update. Preserve existing IDs/parameters/events when revising a user's applet unless the requested change requires a migration. `--applet` is repeatable and accepts explicitly supplied applet folders or packages. It does not search or modify an installed library.

Deliver the editable applet and deck sources, a `.mapl` applet package, a `.deck` package and concise setup instructions. The packages have different jobs: `.deck` references an applet ID and does **not** install its files. `.mapl` is a ZIP with `manifest.json`, `applet.html` and assets at its root; one immediate wrapper folder is also accepted by the inspected importer. The packager emits a root layout and refuses to overwrite an existing package or put it inside its source folder.

Have the user open the `.mapl` with MATRIC to install it, then import the `.deck`. The inspected Windows importer installs under the user's Documents folder at `MATRIC\custom\<AppletId>`; Documents can be redirected. Importing the same AppletId replaces that installed applet's directory, affecting every control using it. Do not silently install, replace applets or edit the live library while authoring/testing. If the editor still shows an old or unavailable applet, refresh its applet catalog where supported, or reopen the editor/reload the client. Keep the applet dependency clear in the deck description and supply setup-guide URLs when referring to a published guide.

## Manifest

Use exact authored names and PascalCase keys. The helper accepts compatible casing such as legacy `AppletID`, but rejects duplicate or case-ambiguous keys. Its authoring checks are deliberately stricter than permissive native deserialization: explicit ID and display name, known fields, typed defaults and known actions are required.

```json
{
  "AppletId": "my-history-inspector",
  "DisplayName": "History inspector",
  "Description": "Inspect recent values and select a sample.",
  "Author": "",
  "VersionMajor": 1,
  "VersionMinor": 0,
  "AppletParams": [
    {"Name": "SignalVariable", "DisplayName": "Signal variable", "ParamType": "variable", "Default": ""}
  ],
  "EventsDefinition": [
    {"Name": "select-sample", "DisplayName": "Select sample", "Description": "Data: value and index.",
     "AllowedActions": ["ActionSetServerVariables"]}
  ]
}
```

- AppletId contains 1–128 ASCII letters, digits, hyphens or underscores, excluding Windows reserved device names. It is the installed folder identity, not the deck/control ID. Use `VersionMajor`/`VersionMinor` for applet revisions, independently of the skill/project/deck versions.
- AppletParams is an array of unique named definitions. ParamType is `string`, `number`, `bool`, `list`, `variable` or `color`. A `variable` parameter holds a server-variable **name**, not its current value. ListItems contains `{ "Text": "Label", "Value": "stored string" }` choices; Default is a stored value. Missing control overrides use applet-defined defaults. The HTML implementation must also establish defaults; the host sends the saved override dictionary, not guaranteed merged manifest defaults.
- EventsDefinition declares events that may carry JSON-compatible `Data`. Choose stable names and document each payload, its units/range and whether it represents a pulse or held input. Emit events only for deliberate interaction, never as an automatic reaction to parameters or feedback.
- AllowedActions contains **runtime ActionId names** accepted by the custom-event editor, short or qualified. They can differ from serialized ActionTypeName: the manifest uses `ActionSetServerVariables`, while a configured deck action uses `EXM.MatricPro.Actions.ActionSetServerVariable`. Inspect catalog `action_id` and templates instead of mechanically deriving one from the other. Custom event definitions do not inherit native controls' event cardinality flags in the inspected editor. A permitted action still needs the correct event payload; manifest permission alone cannot prove its semantics.

## Deck container

Create `new_control("MCCustom", ..., x, y, width, height)` with grid-cell dimensions, then configure:

```json
{
  "AppletId": "my-history-inspector",
  "AllowInteraction": true,
  "AllowedFeatures": "",
  "AppletParams": {"SignalVariable": "my_verified_signal"}
}
```

Use `AllowedFeatures: ""` unless the applet actually needs a specific iframe permission. Assign normal native actions in `ControlEvents` under the exact manifest event name. Action calculations receive the applet's payload as `eventData`, for example `eventData.value`. The manifest-aware deck check verifies event names, allowed action identities, parameter override types/list choices, normal action configuration, navigation and resources. Without a supplied manifest, dynamic events cannot be certified; the generic checker keeps them as errors and warns about the separate applet dependency.

The applet's values arrive through the message bridge below; it does not inherit the native control's text/config binding system. Use verified application variables or explicitly configured user variables. `ReferencedUserVariables` metadata alone is not proof that importing the deck installs calculated/user variables. Explain any required variable creation in setup instructions. A web preview must not install variables or operate applications merely to make the demo look live.

For DCS panels, `dcs_bios.py check ... --applet /path/to/applet` also accepts repeatable applet sources. It audits `variable` parameters (including manifest defaults) as telemetry dependencies, alongside the usual literal commands and binding transforms. It cannot discover arbitrary names constructed inside applet JavaScript; document and select all such outputs in DBMM explicitly.

## Iframe message contract

The host loads `/custom/<AppletId>/applet.html?...#<ControlId>`. Read `window.location.hash.slice(1)` for this instance's control ID. Distinguish simultaneous instances even when they use the same applet. The starter's `bridge.js` implements the contract without an external SDK.

| Direction | Message | Payload |
| --- | --- | --- |
| Host → applet | `PARAMSUPDATE` | Saved AppletParams dictionary |
| Host → applet | `VARIABLESUPDATE` | Map of variable names directly to values, without `.Value` |
| Host → applet | `RESIZE` | `{containerWidth, containerHeight}` in CSS pixels |
| Applet → host | `cce-<ControlId>` | `{EventName: "select-sample", Data: {value: 42, index: 3}}` |
| Applet → host | `cce-<ControlId>` | `{EventName: "reqvariables", Data: null}` to request a snapshot |

Example event:

```javascript
window.parent.postMessage({
  messageId: 'cce-' + window.location.hash.slice(1),
  payload: {EventName: 'select-sample', Data: {value: 42, index: 3}}
}, '*');
```

Validate incoming messages with `event.source === window.parent` and check message/payload shapes. Keep zero and false as values; test presence rather than truthiness. Render data with textContent or safe SVG attributes. Register listeners before requesting the first variable snapshot, handle variables and parameters arriving in either order, and avoid requesting again unconditionally on every PARAMSUPDATE (the host can resend parameters with a variable response). The starter requests again only when its selected variable name changes.

The inspected host optionally accepts `reqvariables.Data.variablePrefixes` (up to 16 nonempty prefixes) and `revisionVariable`. These are performance extensions; legacy hosts may send the full map. Select exact known names from the received snapshot and do not assume a revision variable exists. The starter uses one selected variable's prefix and no revision dependency.

## Input lifecycle and responsiveness

For a pulse such as sample selection, emit on a completed pointer/touch interaction. A pointer cancellation must not commit an action. For controls that hold a keyboard/mouse/joystick action, explicitly balance release on pointer-up, pointercancel, blur, hidden/pagehide and teardown. In the inspected implementation, generic `release` cancels held `press` actions and `<event>-release` cancels its matching event; suffix release messages are cleanup signals, not independent action events. Do not declare `reqvariables`, `__cancel_applet_inputs` or suffix-release signals as bindable manifest events. Lifecycle handling has evolved: verify the target version before relying on host cancellation, and test release behavior with that version. Avoid held inputs when a pulse suffices.

The host disables interaction in editor previews and when AllowInteraction is false. Applets should request data/render in the editor while leaving action emission to explicit client interaction. Cancel/remove listeners and timers when the page/frame goes away; avoid autoplay, polling loops or network calls unrelated to the user's task. The starter has no timers or network dependency and caps history at 120 changed finite numeric values.

Use the iframe's available width/height, responsive layout and pointer-sized targets. A chart may have an internal SVG viewBox; its surrounding interface must still adapt to the container. Avoid fixed desktop-size canvases, document-wide zoom tricks or page-background registration. Test narrow portrait, wider landscape, resizing, long labels, unavailable variables and multiple instances. Keep custom fonts optional and separately installed under the skill's font rules; the starter uses system fonts and the packager rejects bundled font binaries. Review any external resource warnings; JavaScript-created URLs/imports and full browser behavior need separate review.

## Synthetic example and acceptance

```text
python scripts/applet_tool.py example --output /path/to/history-demo
python scripts/applet_tool.py validate /path/to/history-demo/History.mapl
python scripts/deck_tool.py validate /path/to/history-demo/History.deck --applet /path/to/history-demo/History.mapl
```

The example uses an original SVG history plot and native LOW/MID/HIGH buttons. Create NUMBER user variables `skill_demo_signal` and `skill_demo_selection`, initially 0, as its SETUP.txt explains. The native buttons update the signal; touching the applet emits a sample selection that a native variable action stores, and a native readout displays it. No real OBS/DCS/system input is configured. This illustrates complete authoring rather than asserting that a custom applet is necessary for a simple numeric readout.

Static checks cover manifest types/names, event/action permission, local HTML/CSS resource references, ZIP layout/path/size limits and deck integration. They do not execute JavaScript, prove arbitrary payload calculations, inspect every dynamically referenced asset, establish applet trust or certify a native installation. Review executable applet code and any network/credential requirements before delivery. Never put credentials or private applet/user files in this public skill.

For maintainer acceptance, independent Python and Node tests require no MATRIC installation. An optional native harness in the repository accepts an explicitly supplied MATRIC build and the generated packages, installs/imports only into isolated temporary directories and executes no actions. Actual device/iframe behavior and real action semantics remain target-version checks.

## Implementation evidence

Verified against the separate MATRIC checkout on 2026-10-25: `CustomAppletManifest.cs`, `CustomAppletParamDef.cs`, `CustomAppletEvent.cs`, `CustomAppletCatalog.cs`, `AppletImporter.cs`, `MCCustomConfig.cs`, `desktop/deck-controls/src/DeckControls/MCCustom.vue`, `CustomControlEvents.vue`, `CustomAppletInputSession.cs` and the `.mapl` import branch in `desktop/MatricServer/Program.cs`. Source inspection establishes this contract; it does not establish availability in an older published MATRIC release. No MATRIC implementation files or bundled proprietary applet assets are distributed with this skill; the starter is original MIT-licensed content.
