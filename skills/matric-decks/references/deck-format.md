# MATRIC deck format

## Package and staging layout

A distributable `.deck` is a ZIP. The current importer expects exactly one outer folder matching the deck's `Id`:

```text
<deck.Id>/deck2.json
<deck.Id>/panel.svg
<deck.Id>/optional-subfolder/other-resource.png
```

The local staging folder has `deck2.json` directly inside it. The packager adds the outer ID folder. Use UTF-8 JSON, exact PascalCase property names and case-sensitive resource references. The current code exports `DeckFileVersion: 3`; old `deck.json` is a different legacy format. Native format version 2 input is recognized by the validator, but new output uses the bundled current version.

## Deck and page

```json
{
  "Id": "fresh-deck-guid",
  "Title": "My panel",
  "Author": "",
  "Description": "",
  "DeckFileVersion": 3,
  "ReferencedUserVariables": [],
  "DefaultPageId": "page-guid",
  "Pages": [{
    "Id": "page-guid",
    "Title": "Main",
    "Cols": 6,
    "Rows": 4,
    "BackgroundColor": "#111827",
    "BackgroundImage": null,
    "BackgroundSize": "cover",
    "Controls": []
  }]
}
```

Use real UUIDs for newly authored deck/page/control identities; the strings above explain the relationships. Page titles are not page IDs. Navigation points to the page ID. Each control has integer `X`, `Y`, `Width`, `Height` measured in grid cells, with a zero-based origin at the upper left. Keep controls inside `Cols` and `Rows`. Overlaps may be intentional for layered designs; the validator reports them as warnings.

## Client scaling and backgrounds

MATRIC is a screen-adaptive control deck, not a UI framework for pixel-perfect layouts. `Cols`/`Rows` express logical grid proportions, not a fixed-resolution canvas. The client adapts rendering to its available screen dimensions, so a deck authored for one tablet can look different on another display or orientation.

The inspected Vue client uses a viewport-sized page container and derives grid-cell size from `min(clientWidth / Cols, clientHeight / Rows)`. Control rendering also rounds cell size down. The page background separately uses CSS `background-size` from `BackgroundSize`: for example, `cover` can scale and crop an image independently of the grid. Centering, unused space and rounding can therefore break alignment between background artwork and controls. Matching the background's pixel dimensions or aspect ratio to the authored grid does not guarantee registration on client screens.

- Avoid complete panel backgrounds whose labels, frames, windows or knob artwork must line up exactly with separate controls. Do not depend on transparent hit targets over a painted page to reproduce a fixed screenshot.
- Put appearance that needs local alignment into the control's own resources and configuration: button `BackgroundImage`, rotary `DialImage`/`ButtonImage`, and native text or feedback bindings. A display bezel and its text should belong to the same control rather than different page layers.
- For a shared display with multiple telemetry fields, prefer one display control with its own bezel and a binding transform that composes the fields. Use literal `variables['name']` references and audit every dependency; separate transparent text controls over page-painted windows recreate the alignment problem.
- Use page backgrounds for a plain color, subtle texture or decoration that tolerates cropping and movement relative to controls. Leave spacing around controls and choose readable text and usable touch targets as the page scales.
- On both new decks and revisions, temporarily hide/remove the page background: all operational labels, bezels and state displays must remain attached to their controls. Remove shared fascia, keypad plates and frames if they depend on exact registration with other controls. Nonessential decoration that tolerates movement can remain.
- Check the intended client and differing screen proportions when available, including clipping and readable labels. Treat static authoring previews and offline models of client CSS as approximations, not native app captures; structural validation cannot establish visual alignment or usability on a device.

Current authoring must not rely on a future proportion-preserving rendering mode. A different mode needs explicit support in the target client before it can justify fixed-canvas composition; an editor preview or matching tablet aspect ratio is not that evidence.

## Controls

Use the exact `ControlTypeName` and corresponding `ControlConfigTypeName`. For example, a button uses `EXM.MatricPro.Controls.MCButton` and `EXM.MatricPro.Controls.Config.MCButtonConfig`. Its appearance/behavior is in `Config`; events are in `ControlEvents`:

```json
{"Name": "release", "Actions": [{"ActionTypeName": "EXM.MatricPro.Actions.ActionGoToPage", "TargetPageId": "another-page-id"}]}
```

Get full templates and field metadata using `deck_tool.py catalog --control MCButton` or another catalog key. Copy defaults rather than constructing a partly specified control. `new_control` supplies the commonly omitted appearance defaults and ID.

For a native touchpad, use `new_control("MCTouchpad", ...)`: its event is `touchpad`, matching the control definition and client. The raw runtime-constructor template retains an older `valuechange` name; the helper corrects it for newly generated controls. This native touchpad is separate from the excluded Stream Deck touch-strip feature.

`FontFace: "text"` means normal text; `FontFace: "icon"` means a Material Design icon name in `Text` (for example, `mdi-microphone`). Custom FontFace values depend on fonts separately installed in MATRIC. `TextSize` and `Padding` are percentages relative to a grid cell. Native alignment values include `Halign: "center"` and `Valign: "mid"`; do not substitute `middle`. Slider geometry is also percentage-based inside its control bounds.

`Config.ControlBindings` is an array of `{ "PropertyPath": "...", "VariableName": "...", "Transform": "..." }`. PropertyPath is a client-state property path, not necessarily the C# configuration property name. Reuse a verified binding or inspect the relevant MATRIC client component. Transform is an optional JavaScript function body receiving `value` and `variables`; an omitted transform binds the value directly. Do not invent built-in variable names.

## Actions and events

An action's discriminant is `ActionTypeName`, the implementation class's full name. It is not the configuration class name. The converter resolves the corresponding configuration type. Internal action IDs can differ from serialized type names: Set variable serializes as `EXM.MatricPro.Actions.ActionSetServerVariable` (singular), while its internal ID ends in `ActionSetServerVariables`. The catalog keys and event maps use serialized implementation names; `action_metadata` also accepts the old internal ID as a lookup alias. Assembly-qualified `ActionType` strings and computed `FileResources` arrays are not needed in newly authored JSON.

Names and serialization matter: buttons expose `press` and `release`; sliders expose `valuechange`, not `change`. Some actions are exclusive or single-instance for an event. Native sliders can bind native volume actions; they cannot host the excluded continuous Stream Deck slider mapping. Inspect the catalog's event map before attaching actions.

Action JSON can contain numeric enums or string enums depending on the original C# definition. The catalog's `properties.<field>.enum` gives the actual JSON representation. For instance, OBS `Command` and audio mute `Command` serialize as names. Do not replace them with an arbitrary UI label or guess an enum ordinal.

## Resources and dependencies

Page backgrounds and native control image fields refer to resource files inside the deck directory. Mobile audio uses `AudioFileName`, also bundled. PC audio uses `AudioPath`, which is a machine-specific external path. Custom fonts, custom applet installations, native drivers and plugin installations need separate setup. Do not quietly embed a local executable, credentials or an entire OBS configuration into a deck.

For an existing deck, preserve all original resource files and unknown root metadata. Stream Deck action resources have separate ownership and remapping rules. The validator warns about those actions but does not certify their resource snapshots or settings. Use MATRIC's own Save As/copy/export workflow for cloning plugin-owned identities/resources.

## Fonts and optional fidelity

MATRIC intentionally does not package fonts with decks: users must obtain fonts separately, avoiding MATRIC facilitating unauthorized redistribution of copyrighted font files. Do not include font binaries in the `.deck`, editable source bundle or embedded resources. A saved font-family name does not install a font, and a font available on the author's Windows system is not evidence that another user's MATRIC installation or client can use it.

Prefer `FontFace: "text"` (MATRIC's default text font) for portable output. Do not make labels, state information or layout depend on a particular unverified font. A custom font can be an optional fidelity enhancement, such as emulating a seven-segment numeric display. When appropriate:

- Specify the exact recommended font family/variant and why it suits the display; check the required digits, punctuation and letters rather than assuming a numeric font covers alphanumeric cockpit text.
- Provide a verified publisher/author download link and ask the user to observe its license. Do not download/install it for them or redistribute it as part of deck generation.
- Explain that the font is a separate user-installed dependency and that missing it means a fallback appearance, not a faithful segmented display. Keep essential information readable with the default font and recheck fit after a font change.

Give these MATRIC installation steps with a recommendation:

1. Download the recommended font from its legitimate source and extract the `.ttf` or `.otf` files.
2. Copy those files into the user's Windows Documents folder under `MATRIC\fonts` (normally `C:\Users\<user>\Documents\MATRIC\fonts`; Documents may be redirected, for example to OneDrive). This is MATRIC's fonts directory, not the deck's resource directory; installing only into Windows is not the MATRIC installation step.
3. Reopen the font list and choose the installed family under the control's **Font type**. If it has not appeared, restart MATRIC and reconnect/reload the client, then check the actual editor/client display.

Use `Config.FontFace` for the selected family rather than locking a different `font-family` into `LabelCustomCSS` or `LabelCustomCSSActive`. In the inspected renderer, custom CSS follows the selected-font styling and can override it; the properties CSS preview applies them in the opposite order. Remove conflicting font-family declarations from both states before diagnosing a font-selector failure. Structural validation does not establish font availability, licensing or rendering fidelity.

## Scope of the helpers

The Python validator is an authoring check against a versioned runtime catalog. It catches wrong field types, enum values, event/action mismatches, IDs, geometry, missing native resources and broken navigation. It does not replace native deserialization/import testing. Applet-defined events are dynamic and need the actual manifest; the generic catalog cannot validate them. Future types/fields need a refreshed catalog. Overlap warnings and external dependency warnings need human interpretation, not automatic deletion of controls.
