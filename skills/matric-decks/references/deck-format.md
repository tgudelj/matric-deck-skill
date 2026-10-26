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

## Deck descriptions and companion guides

`Description` is import-facing metadata. Make it concise and understandable without knowledge of MATRIC internals: state the deck's purpose and the intended client device size, aspect ratio, and orientation. Use only device facts that are known; when authoring against an assumption, identify it as such. For example: "F/A-18C Up Front Controller for a 9-inch, 16:10 landscape tablet."

Do not fill the description with grid dimensions, control-class names, action/binding identifiers, variable names, archive details, or other authoring mechanics. Put required integrations, installation steps and troubleshooting in delivery notes or a companion guide instead.

When the description mentions a companion setup guide, include its stable, user-accessible URL in the description. Never use a generic "see the companion guide" instruction, fabricate a link, or imply that a local source file is an online guide. If a suitable URL has not been supplied or published, omit that reference from the description and provide the setup material separately.

There are two required exceptions to the usual concise description:

- A deck using DCS-BIOS through DCS-BIOS-MATRIC-Middleware (DBMM) must include these lines, exactly including both URLs:

  ```text
  DBMM installation with DCS-BIOS is required
  DBMM: https://github.com/tgudelj/DCS-BIOS-MATRIC-Middleware/releases
  DCS-BIOS: https://github.com/DCS-Skunkworks/dcs-bios/releases/
  ```

- A deck using a non-standard font must name the font and provide its permitted download URL. For example: `For best visual results, install Transponder AOE font from: https://www.dafont.com/transponder-aoe.font`. Font URLs may point only to `https://www.dafont.com/` or `https://fonts.google.com/`; do not link to any other font site.

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

## Target screens and touch usability

Fitting the logical grid on screen is not the same as making it usable by touch. The same deck can be comfortable on a 9-inch tablet yet have tiny keys, unreadable labels and cramped rotary gestures on a smartphone, even when that phone has a high pixel resolution.

- Use the intended device model or approximate physical screen dimensions/diagonal, resolution/aspect ratio, and portrait/landscape orientation as layout inputs. Allow for the actual client area after system/navigation bars. Diagonal alone does not give aspect ratio; pixel dimensions alone do not give physical size.
- Ask for missing screen information when it would materially change layout choices. If proceeding without it, state the assumed target and keep the layout provisional rather than claiming usability across devices.
- Choose grid density, control spans and spacing so touch targets and text remain usable on the intended screen. Consider the interactive region, not just the artwork: rotary gestures and the halves of a multi-position switch need enough room for fingers.
- For a smaller device, simplify the panel or split controls into task-focused pages with clear navigation instead of uniformly shrinking a dense tablet design. If both phones and tablets must be supported, design around the smallest intended device or offer separate layouts with the user's agreement.
- Review at the intended physical scale when possible and seek actual-device feedback on readability, accurate taps and gestures. A desktop screenshot, matching aspect ratio or passing bounds check does not establish touch usability. Do not claim precise physical target sizes without screen/viewport measurements.

## Controls

Use the exact `ControlTypeName` and corresponding `ControlConfigTypeName`. For example, a button uses `EXM.MatricPro.Controls.MCButton` and `EXM.MatricPro.Controls.Config.MCButtonConfig`. Its appearance/behavior is in `Config`; events are in `ControlEvents`:

```json
{"Name": "release", "Actions": [{"ActionTypeName": "EXM.MatricPro.Actions.ActionGoToPage", "TargetPageId": "another-page-id"}]}
```

Get full templates and field metadata using `deck_tool.py catalog --control MCButton` or another catalog key. Copy defaults rather than constructing a partly specified control. `new_control` supplies the commonly omitted appearance defaults and ID.

For a native touchpad, use `new_control("MCTouchpad", ...)`: its event is `touchpad`, matching the control definition and client. The raw runtime-constructor template retains an older `valuechange` name; the helper corrects it for newly generated controls. This native touchpad is separate from the excluded Stream Deck touch-strip feature.

`FontFace: "text"` means normal text; `FontFace: "icon"` means a Material Design icon name in `Text` (for example, `mdi-microphone`). Custom FontFace values depend on fonts separately installed in MATRIC. In the inspected `deck-controls-mixin.js`, `TextSize` produces pixels as `cellSize * min(Height, Width) * TextSize / 100` when both spans are present (otherwise `cellSize * TextSize / 100`). It is relative to the control's shorter dimension, while `Padding` uses `cellSize * Padding / 100`. A 9-cell-tall square control at TextSize 10 therefore renders text at 90% of a cell, not 10%. Check the target renderer and recheck text after resizing rather than keeping a fixed size across different spans. Native alignment values include `Halign: "center"` and `Valign: "mid"`; do not substitute `middle`. Slider geometry is also percentage-based inside its control bounds.

`Config.ControlBindings` is an array of `{ "PropertyPath": "...", "VariableName": "...", "Transform": "..." }`. PropertyPath is a client-state property path, not necessarily the C# configuration property name. Reuse a verified binding or inspect the relevant MATRIC client component. Transform is an optional JavaScript function body receiving `value` and `variables`; an omitted transform binds the value directly. Do not invent built-in variable names.

## Actions and events

An action's discriminant is `ActionTypeName`, the implementation class's full name. It is not the configuration class name. The converter resolves the corresponding configuration type. Internal action IDs can differ from serialized type names: Set variable serializes as `EXM.MatricPro.Actions.ActionSetServerVariable` (singular), while its internal ID ends in `ActionSetServerVariables`. The catalog keys and event maps use serialized implementation names; `action_metadata` also accepts the old internal ID as a lookup alias. Assembly-qualified `ActionType` strings and computed `FileResources` arrays are not needed in newly authored JSON.

Names and serialization matter: buttons expose `press` and `release`; sliders expose `valuechange`, not `change`. Some actions are exclusive or single-instance for an event. Native sliders can bind native volume actions; they cannot host the excluded continuous Stream Deck slider mapping. Inspect the catalog's event map before attaching actions.

Action JSON can contain numeric enums or string enums depending on the original C# definition. The catalog's `properties.<field>.enum` gives the actual JSON representation. For instance, OBS `Command` and audio mute `Command` serialize as names. Do not replace them with an arbitrary UI label or guess an enum ordinal.

## Resources and dependencies

Page backgrounds and native control image fields refer to resource files inside the deck directory. Mobile audio uses `AudioFileName`, also bundled. PC audio uses `AudioPath`, which is a machine-specific external path. Custom fonts, custom applet installations, native drivers and plugin installations need separate setup. Do not quietly embed a local executable, credentials or an entire OBS configuration into a deck.

## Reusing installed control templates

When the user's MATRIC deck library is available, use its pre-installed template decks as a visual source before designing new artwork. Find them by their visible deck titles, not a hard-coded library folder or deck ID:

- For ordinary decks, inspect **Default control templates**.
- For a DCS deck, inspect **Aviation button templates** first for aviation-style skeuomorphic controls, then **Default control templates**.

These decks are a convenience, not an input requirement: users may have deleted them, and the portable skill must not ship their artwork. If neither deck is available or no design fits, use native visual configuration and the user's brief; create original artwork only when it materially improves a requested look.

To reuse a design, start with a newly generated control of the appropriate catalog type and fresh ID. Transfer only the visual fields that fit the target (for example, colors, text styling, `BackgroundImage`, `DialImage`, `ButtonImage`, and state visuals) and copy each referenced normal, pressed, active, or state resource into the staged deck. Then create the target's layout, bindings and actions from its actual requirements. Never carry over the template control's `ControlEvents`, bindings, variables, control ID, navigation, or plugin-specific settings merely because its appearance is useful. Validate that every transferred resource is packaged and that the target remains complete when the page background is hidden.

For an existing deck, preserve all original resource files and unknown root metadata. Stream Deck action resources have separate ownership and remapping rules. The validator warns about those actions but does not certify their resource snapshots or settings. Use MATRIC's own Save As/copy/export workflow for cloning plugin-owned identities/resources.

Custom applet files have separate ownership too: an `MCCustom` container references a separately installed AppletId. Use the [custom applet workflow](custom-applets.md) to create/validate the manifest, package a `.mapl`, and check deck events/parameters with `deck_tool.py validate ... --applet /path/to/applet`. A `.deck` archive alone does not install applet files.

## Fonts and optional fidelity

MATRIC intentionally does not package fonts with decks: users must obtain fonts separately, avoiding MATRIC facilitating unauthorized redistribution of copyrighted font files. Do not include font binaries in the `.deck`, editable source bundle or embedded resources. A saved font-family name does not install a font, and a font available on the author's Windows system is not evidence that another user's MATRIC installation or client can use it.

Prefer `FontFace: "text"` (MATRIC's default text font) for portable output. Do not make labels, state information or layout depend on a particular unverified font. Use a non-standard font only when it is genuinely important to the requested look and feel, such as emulating a seven-segment numeric display. Do not use one merely as decoration. If it is not clear that the visual benefit justifies the extra installation, explain that it is optional, say in plain language that it is not included with the deck and must be installed in MATRIC's fonts folder, then ask the user whether they want it before selecting it. When appropriate:

- Specify the exact recommended font family/variant and why it suits the display; check the required digits, punctuation and letters rather than assuming a numeric font covers alphanumeric cockpit text.
- Use or recommend only a font available from [DaFont](https://www.dafont.com/) or [Google Fonts](https://fonts.google.com/). The deck description must state the exact font name and link directly to its page on one of those two sites; do not include font links to any other site. Ask the user to observe the font's license. Do not download/install it for them or redistribute it as part of deck generation.
- Explain that the font is a separate user-installed dependency and that missing it means a fallback appearance, not a faithful segmented display. Keep essential information readable with the default font and recheck fit after a font change.

Give these MATRIC installation steps with a recommendation:

1. Download the recommended font from its legitimate source and extract the `.ttf` or `.otf` files.
2. Copy those files into the user's Windows Documents folder under `MATRIC\fonts` (normally `C:\Users\<user>\Documents\MATRIC\fonts`; Documents may be redirected, for example to OneDrive). This is MATRIC's fonts directory, not the deck's resource directory; installing only into Windows is not the MATRIC installation step.
3. Reopen the font list and choose the installed family under the control's **Font type**. If it has not appeared, restart MATRIC and reconnect/reload the client, then check the actual editor/client display.

Use `Config.FontFace` for the selected family rather than locking a different `font-family` into `LabelCustomCSS` or `LabelCustomCSSActive`. In the inspected renderer, custom CSS follows the selected-font styling and can override it; the properties CSS preview applies them in the opposite order. Remove conflicting font-family declarations from both states before diagnosing a font-selector failure. Structural validation does not establish font availability, licensing or rendering fidelity.

## Scope of the helpers

The Python validator is an authoring check against a versioned runtime catalog. It catches wrong field types, enum values, event/action mismatches, IDs, geometry, missing native resources and broken navigation. It does not replace native deserialization/import testing. Applet-defined events are dynamic: supply their manifests through `--applet` for event/action and parameter checks; the generic catalog alone cannot validate them. Future types/fields need a refreshed catalog. Overlap warnings and external dependency warnings need human interpretation, not automatic deletion of controls.
