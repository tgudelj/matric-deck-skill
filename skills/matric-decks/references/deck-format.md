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

An action's discriminant is `ActionTypeName`, the implementation class's full name. It is not the configuration class name. The converter resolves the corresponding configuration type. Assembly-qualified `ActionType` strings and computed `FileResources` arrays are not needed in newly authored JSON.

Names and serialization matter: buttons expose `press` and `release`; sliders expose `valuechange`, not `change`. Some actions are exclusive or single-instance for an event. Native sliders can bind native volume actions; they cannot host the excluded continuous Stream Deck slider mapping. Inspect the catalog's event map before attaching actions.

Action JSON can contain numeric enums or string enums depending on the original C# definition. The catalog's `properties.<field>.enum` gives the actual JSON representation. For instance, OBS `Command` and audio mute `Command` serialize as names. Do not replace them with an arbitrary UI label or guess an enum ordinal.

## Resources and dependencies

Page backgrounds and native control image fields refer to resource files inside the deck directory. Mobile audio uses `AudioFileName`, also bundled. PC audio uses `AudioPath`, which is a machine-specific external path. Custom fonts, custom applet installations, native drivers and plugin installations need separate setup. Do not quietly embed a local executable, credentials or an entire OBS configuration into a deck.

For an existing deck, preserve all original resource files and unknown root metadata. Stream Deck action resources have separate ownership and remapping rules. The validator warns about those actions but does not certify their resource snapshots or settings. Use MATRIC's own Save As/copy/export workflow for cloning plugin-owned identities/resources.

## Scope of the helpers

The Python validator is an authoring check against a versioned runtime catalog. It catches wrong field types, enum values, event/action mismatches, IDs, geometry, missing native resources and broken navigation. It does not replace native deserialization/import testing. Applet-defined events are dynamic and need the actual manifest; the generic catalog cannot validate them. Future types/fields need a refreshed catalog. Overlap warnings and external dependency warnings need human interpretation, not automatic deletion of controls.
