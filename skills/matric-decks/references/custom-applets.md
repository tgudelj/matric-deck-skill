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
    {"Name": "Padding", "DisplayName": "Edge padding in pixels", "ParamType": "number", "Default": 0},
    {"Name": "BackgroundColor", "DisplayName": "Background color", "ParamType": "color", "Default": "#101827"},
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

## Required appearance parameters

Every new applet must declare `Padding` as a `number` parameter and `BackgroundColor` as a `color` parameter. Define the same defaults in the HTML/JavaScript implementation because the host may send only saved overrides. Use nonnegative CSS pixels for the inset from all four iframe edges; validate finite values and document any maximum. Apply this inset before computing a proportional fit, so it does not shrink or grow with the artwork. Clamp effective padding for very small frames so the remaining content area never becomes negative.

Paint the entire iframe with BackgroundColor, including the padding and unused aspect-ratio margins. Do not leave hardcoded html/body backgrounds covering that setting. Validate color values (for example with `CSS.supports('color', value)`) and preserve previous values on missing/invalid parameter updates. A transparent default is appropriate when the design should inherit the deck's appearance; support alpha values when the target color picker supplies them. Keep intentional internal dial/card/display surfaces distinct from the configurable outer background.

Test zero and nonzero padding, background changes, partial updates, malformed values and resizing. Verify actual content bounds and computed background colors; hiding overflow alone does not prove that the content fits. Supply these parameters in example manifests and delivery notes.

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

Use the iframe's available width/height after configurable padding. When the user wants a small control to preview the full composition, proportionally fit a design canvas inside that area and center unused space, preserving composition instead of reflowing or hiding details. Touch targets scale with that design, so enlarge the actual control for comfortable interaction. Use responsive reflow when it suits the requested behavior. Avoid document-wide zoom tricks or page-background registration. Test narrow portrait, wider landscape, resizing, long labels, unavailable variables and multiple instances. Keep custom fonts optional and separately installed under the skill's font rules; the starter uses system fonts and the packager rejects bundled font binaries. Review any external resource warnings; JavaScript-created URLs/imports and full browser behavior need separate review.

### Fitting in editor and client frames

Start HTML with `<!doctype html>`. For a design of width `W` and height `H`, calculate `scale = min((viewportWidth - 2 * padding) / W, (viewportHeight - 2 * padding) / H)` after clamping padding to leave a positive area. Center the design, set its explicit dimensions and transform origin, and apply a CSS transform to that element. Do not calculate scale from the already transformed element or apply document-wide `body.style.zoom`. A fixed composition should not depend on viewport media queries that unexpectedly rearrange it in a small editor frame.

Fit after DOM initialization, on viewport resize and host RESIZE, and observe the actual viewport/container with ResizeObserver. Hidden editor frames can initialize at zero size; recompute when they become visible. Keep observer callbacks idempotent: observe the viewport for fixed designs, and avoid size feedback loops when measuring dynamic content. For lists such as mixer channels, derive design extent from content rather than silently cropping or adding scrollbars. Offer an explicit layout choice if portrait and landscape compositions are useful. Optional compact views, such as a date-only calendar, should use the space remaining after padding and return to the full view when enlarged; do not make compact reflow the default substitute for a requested zoomed-out preview.

Convert gesture positions into the design element's local coordinates. For example, `localX = (clientX - rect.left) * element.clientWidth / rect.width`; do not assign screen coordinates directly to a transformed joystick indicator. Test the emitted normalized values as well as the indicator position, center/reset and release behavior at multiple scales.

Version changed stylesheet/script URLs or use content-hashed names. A fresh HTML document can otherwise load cached assets from a previous applet revision. Distinguish that possibility from an observed cause: standalone rendering does not establish why a running editor failed. Test nested sandboxed iframes, hidden-to-visible startup, parent transforms, repeated frame resizing and stale/missing assets where relevant. Verify both bounds and visible output; document overflow:hidden alone can conceal a broken fit.

When debugging an iframe control or a custom applet in MATRIC, starting the MATRIC server with the `-dev` command-line argument opens developer tools. This optional debugging mode can help inspect console errors, DOM/CSS layout and loaded resources in the actual host.

### Display widgets and local state

For a display-only request, omit interactive DOM controls, focus targets and bindable action events; request variable snapshots only as needed. Keep histories bounded, accept zero as a value, define invalid/stale data behavior, and show gaps rather than fabricated live samples. Use numerically stable scaling for extreme finite values. Distinguish sampling unchanged values at a time interval from recording only value changes.

Use timestamps for countdown/stopwatch calculations rather than decrementing once per timer callback; background throttling must not slow elapsed time. State whether navigation/reload resets the timer and whether timing follows the device clock. For persistent counters, key storage by control identity and disclose that browser storage is per device/origin, not server-synchronized or durable accounting storage. Handle unavailable/malformed storage. Parameter-only visual changes should not reset accumulated state; describe settings that intentionally do so.

For clocks/calendars, offer named timezone choices rather than requiring users to know IANA identifiers. Store stable timezone values separately from custom display labels; use the target browser's Intl rules for regional dates and daylight saving. Searchable list rendering is a MATRIC-editor capability, not a new manifest parameter type: verify the target editor before promising autocomplete. When font-independent graphics are requested, use SVG paths/shapes or explicit graphic glyphs, document supported label characters, and test unsupported characters and long labels without bundling fonts.

### Demonstrations, revisions and embedded interfaces

Clearly label synthetic data. If a demo has sliders/mute/buttons, handle those actions against simulated state and prevent their events from reaching real device/application bindings. Keep real discovery separate from the synthetic list. Preserve existing live-mode defaults when updating a live applet; an example deck may explicitly enable demo mode. Do not infer real device IDs from synthetic names.

When variants differ only by a setting, prefer one applet identity with a typed parameter. Define exactly what a setting reverses (for example, a color ramp versus fill direction), retain parameter/event names where compatible, and provide migration instructions for old applet IDs and custom thresholds. Importing the new applet does not migrate controls referring to a different ID or authorize deleting the old installation.

Before adapting a bundled applet, compare its available source with the actual bundled runtime. Do not rebuild an older checkout over a newer runtime and lose existing behavior. If a fitting shell is justified around an existing interface, validate messages from the immediate child, relay only the required protocol, preserve the outer control ID, and test real event payloads. `window.top.postMessage` can bypass that shell and cause the MATRIC host's source check to reject actions; use the immediate parent at each layer. Cache startup snapshots until the child is ready and handle reload/resume without duplicating listeners. Refresh provenance hashes for modified assets or omit stale metadata and explain the adaptation. Keep proprietary/user artifacts out of the distributed skill.

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
