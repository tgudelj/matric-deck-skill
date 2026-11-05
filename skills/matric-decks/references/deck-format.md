# MATRIC deck format

## Package and staging layout

A distributable `.deck` is a ZIP. The current importer expects exactly one outer folder matching the deck's `Id`:

```text
<deck.Id>/deck2.json
<deck.Id>/panel.svg
<deck.Id>/other-resource.png
```

The local staging folder has `deck2.json` directly inside it. The packager adds the outer ID folder. Use UTF-8 JSON, exact PascalCase property names and case-sensitive resource references. The current code exports `DeckFileVersion: 3`; old `deck.json` is a different legacy format. Native format version 2 input is recognized by the validator, but new output uses the bundled current version.

**Mandatory flat layout:** every image, audio file and other deck asset must sit beside `deck2.json`. No subfolders are allowed inside that deck folder; nested resources do not work correctly in MATRIC. Resource references must be filenames only, for example `button-off.png`, not `art/button-off.png` or `art\\button-off.png`. The single outer `<deck.Id>/` archive folder is required and does not count as a resource subfolder. Separately installed `.mapl` applets have their own packaging rules.

For an existing deck with nested resources, stage a copy, give conflicting basenames unique filenames, move assets beside `deck2.json`, and update every affected reference and resource list. Preserve the original input and do not silently discard colliding assets or guess opaque plugin-owned paths. The helper rejects nested input rather than automatically flattening or claiming native compatibility.

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

MATRIC officially supports at most **50 columns and 50 rows per page**, with both values positive integers. This maintainer-confirmed application limit applies to operational decks, inventories and templates. A larger page rendering successfully is not evidence of supported behavior: it can affect stability and especially performance. The helper rejects out-of-range pages during validation/packaging and rejects them before creating a new draft. Do not change imported page dimensions automatically merely to pass validation; plan a compact re-layout or resolve any grouping constraint with the user.

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
- On both new decks and revisions, inspect control resources for complete operational labels, bezels and state displays. When suitable rendering is available, also temporarily hide/remove the page background and check that each control remains complete. Remove shared fascia, keypad plates and frames if they depend on exact registration with other controls. Nonessential decoration that tolerates movement can remain.
- Check the intended client and differing screen proportions when available, including clipping and readable labels. Treat static authoring previews and offline models of client CSS as approximations, not native app captures; structural validation cannot establish visual alignment or usability on a device.

Current authoring must not rely on a future proportion-preserving rendering mode. A different mode needs explicit support in the target client before it can justify fixed-canvas composition; an editor preview or matching tablet aspect ratio is not that evidence.

## General machinery and instrument presentation

For any machinery, panel, button box, instrument or individual hardware control represented on a MATRIC screen, use a consistent straight-on frontal view. This applies generally, including industrial equipment, audio consoles, vehicle dashboards, flight panels and racing button boxes. Avoid angled product-shot compositions, oblique/isometric cameras, foreshortening and controls shown from conflicting viewpoints. Texture, highlights, shadows, recesses and bevels can convey physical depth without changing the viewing direction. Keep aligned artwork self-contained on each control and leave final layout/resizing to the user. Follow an explicitly requested alternative presentation when provided.

## Cockpit photographic references and flat-screen presentation

Use the [flight simulator cockpit authoring workflow](flight-sim-cockpits.md) to establish the visual benchmark and review representative controls before extending a design. The user's desired look and feel or selected reference deck governs appearance; the hardware-inspired treatment below is the default when no alternative is specified.

For aircraft cockpit panels and instruments in DCS and other flight simulators, search for real photographs and actually inspect the images before authoring the visual design. Prefer references matching the aircraft variant and panel revision; a supplied suitable real photograph can serve as the reference. Use the photos to establish control shapes, arrangement, legends, colors, materials and surface texture. Do not guess appearance from DCS-BIOS definition names, control categories or input mappings. If suitable photos cannot be accessed, disclose the visual-reference gap rather than describing guessed artwork as an accurate replica. Photographs inform appearance; verified definitions and input mappings still establish behavior. Do not redistribute reference photos as deck assets without permission.

Physical cockpit layout is optional: prioritize the user's workflow, readable legends and touch usability. When depicting cockpit hardware, default to realistic textured control faces, painted metal, molded keycaps, ribbed wheels, restrained wear and material shading as appropriate to the reference, unless the user requests another style. Reuse suitable installed aviation templates first; adapt or create control-owned artwork where needed for the requested look. Generic flat rectangles and labels alone should not be the default visual treatment for depicted cockpit hardware. Realistic materials do not require copying the physical cockpit's control grouping, spacing or dimensions.

By default, design the panel for a flat screen as if viewed directly from in front of its face; follow an explicitly requested alternative presentation. Keep panel faces, keycaps, instruments and rotaries in a consistent straight-on projection. Avoid oblique/isometric compositions, tilted camera views, foreshortened faces or a collage of controls drawn from different perspectives. Material highlights and shallow bevel shading can suggest depth without changing that frontal view. Do not use a perspective illustration merely because it looks three-dimensional in isolation. When suitable rendering is available, review the assembled deck against the photos for both material fidelity and consistent viewing direction before delivery.

Evaluate material realism on each control, not just the page background. A scratched metal background cannot compensate for smooth, generic buttons. Use material-specific detail: soft highlights, slight surface variation and rounded edges for molded keycaps; dark textured faces and substantial rims for round buttons; convincing metal hardware for toggles; recessed, subtly worn bezels and luminous lettering for displays. Keep lighting consistent and wear restrained. Uniform discs, perfect outlines and clean gradients alone often read as software graphics rather than cockpit equipment.

A straight-on presentation can still have convincing depth. Highlights, soft shadows, recesses, bevels and rounded edges should describe the hardware while its face remains frontal; do not interpret the flat-screen rule as requiring flat-looking artwork. Preserve recognizable toggle, rocker, keycap and wheel forms where suitable for the interaction. Merely placing a generic selection button at a physical switch's location does not reproduce its visual character; retain verified input semantics when adapting its appearance.

Assess visual fidelity separately from layout fidelity. A task-focused page combining controls from several cockpit panels can still feel authentic through materials, hardware forms, legends and lighting. Do not copy a reference deck's control grouping merely because its artwork is the desired style. When the user provides a visual benchmark, inspect its actual control images at useful size alongside the generated control assets; compare the assembled rendering when available. Reuse or adapt suitable installed aviation artwork before replacing it with simpler drawings; keep any user-deck artwork local unless redistribution is authorized. Preserve editable native labels when suitable, following the existing font rules for specialized display lettering.

Keep the existing self-contained-control and client-scaling rules: each control owns its aligned labels, bezel, artwork and state display. Page backgrounds may carry stretch-tolerant surface texture, never a photographed fascia requiring independent controls to align with it. Photographic fidelity does not override the user's workflow or touch-layout needs.

## Cockpit control groups and touch regions

Apply these principles to cockpit hardware in any flight simulator, using the selected aircraft's references and verified input path. A reference deck can demonstrate a useful composition without proving that its commands, event handling or feedback fit the target aircraft.

- Preserve local relationships that help identify and operate an assembly: directions around a switch center, the two ends of a rocker, paired engine controls, or selection keys aligned with display rows. The overall page can still combine controls from different cockpit locations to suit the user's tasks. Match the aircraft and requested workflow rather than imposing one aircraft's arrangement on others.
- Choose native controls by interaction. When several buttons can represent a directional switch, use separate momentary regions around a common visual center; the center may be a decorative control with no actions. A finite maintained selector may suit a native multi-position switch instead. Do not infer a joystick gesture, simultaneous-axis support or a need for a custom applet from the assembled appearance. Check the catalog's supported events and use the applet workflow only when native controls cannot express the required interaction.
- Define the complete region that responds to each input as well as the visible artwork. For example, a four-way switch can use four native buttons above, below, left and right of a cap. Place each arrow or legend inside its corresponding button near the cap; the button's entire rectangle remains tappable even where its background or image is transparent. Keep the active rectangles nonoverlapping and the legends readable, preserving recognizable hardware proportions. Judge target size and spacing from those full rectangles at the intended physical screen scale. Check that each direction can be selected without activating its neighbor; enlarge or separate targets, or recompose the group if needed. Do not assume a fixed grid span works on every device. Inspect actual events before treating a legend as decorative, since a printed label may itself be the working button. Keep aligned artwork on its controls, not on the page background.
- Verify every region's action semantics independently: press/release, return to neutral, maintained selection, repeat behavior and any shared-axis dependencies. A directional region needs its complete actuation/release behavior; do not depend on a neighboring button to release it. Use the verified keyboard, joystick or simulator integration path as appropriate, including implicit release where supported. Never generalize command values or timing from another aircraft. Check release at region edges, touch cancellation and rapid direction changes on the target client when available.
- Distinguish decorative hardware, local interaction feedback and actual simulator state. A neutral cap image does not report switch position; a pressed arrow does not prove a mode engaged. Preserve verified feedback when adapting a reference, and bind shared state artwork to the appropriate simulator output when available. If feedback is absent, retain a neutral or clearly local presentation and disclose the limit rather than persisting an assumed aircraft state.
- Treat an intentionally composed assembly as the unit of visual review and reuse. Use descriptive component names so unlabeled arrows remain identifiable in the editor, and document which controls, resources and shared feedback dependencies must travel together. Do not assume copying one native button copies the group or that a grouping feature exists. Template inventories should still favor independently usable components where practical.

Review the assembled group's spatial relationships, touch regions, input behavior and feedback separately. Inspect it with the page background hidden and at the intended and a differing aspect ratio when rendering is available. A convincing cap image or passing structure check does not establish a usable assembly; offline renders and simulated events remain separate from actual-device and live-simulator acceptance.

## Layout composition review

Plan functional groups before assigning individual control bounds. Identify groups such as a keypad, display/selection bank, radio controls and function row, then establish relative sizes, shared baselines and a consistent row rhythm. Align an associated selection button with its display row. Keep a radio's volume, channel display and channel selector in a recognizable group. Prefer smaller gaps within a group than between groups, and allow empty space where it clarifies those relationships.

Preserve characteristic control proportions when the requested appearance or shape-dependent artwork relies on them; do not turn depicted square function keys into wide rectangles merely to fill available width. This is not a fixed aspect-ratio requirement for plain controls; see [control resizing and artwork proportions](#control-resizing-and-artwork-proportions). Equal spacing alone is insufficient when meaningful groups start at unrelated heights or their paired controls no longer align. A UFC, for example, can align its scratchpad with the first option-display row and use a shared row rhythm through the option bank and keypad. This is an example of preserving useful spatial relationships, not a mandatory layout for every panel.

Recompose after changing the grid. Rounding scaled coordinates and spans can alter alignment, gaps, control proportions and group balance even when every control remains within bounds. When suitable rendering is available, compare the assembled panel with the user's reference for grouping, visual hierarchy, relative proportions and interaction pairs. Otherwise complete structural checks, deliver the package and identify rendered visual review as outstanding. Evaluate artwork/material quality and structural/binding checks separately; passing either does not establish a good layout. Adapt relationships to the user's screen and workflow rather than copying unsupported page dimensions or assuming physical cockpit fidelity is always the best touch layout.

## Workflow priorities and control economy

In operational layouts, use familiar interaction patterns, alignment and proximity to communicate clear relationships between controls. For example, a compact mute icon beside a labeled volume slider can identify one audio channel without repeating the source name on the button. Keep related controls closer together than neighboring groups, and retain enough context to distinguish their targets. Preserve descriptive names and descriptions for editing.

Allocate prominent space according to the user's tasks and frequency of use. Discovered source, device and action names establish identity and possible function, not personal importance. Infer routine placement from the request and existing workflow evidence; ask a focused question when choosing among plausible primary controls would materially change usability. Keep secondary functions on task-focused pages where that helps the target screen, without requiring the user to design every control.

Consider consolidating opposing commands into one toggle or state-aware control when a verified action supports the intended behavior and actual-state feedback can make its meaning clear. This can save touch space otherwise consumed by separate start/stop, enable/disable or similar controls. Do not implement this as an assumed local toggle that can drift from the application. Separate commands can remain appropriate when the user prefers them, explicit set-state operation matters, or toggle semantics/feedback are unavailable. Preserve momentary, held and multi-position behavior rather than treating every pair as a toggle.

Fit labels within the actual control face, accounting for bezels, padding, font metrics and active-state styling. Prefer intentional two-line labels where wording needs the room; use the target client's supported line-break representation and keep the function understandable. Check long labels and changed control spans at the intended scale. An approximate preview may wrap or measure text differently from MATRIC, so it cannot establish native label fit; use actual-client evidence when available and identify remaining native text review when it is not. Do not treat reducing font size as the only solution to clipping.

## Target screens and touch usability

Fitting the logical grid on screen is not the same as making it usable by touch. The same deck can be comfortable on a 9-inch tablet yet have tiny keys, unreadable labels and cramped rotary gestures on a smartphone, even when that phone has a high pixel resolution.

- Use the intended device model or approximate physical screen dimensions/diagonal, resolution/aspect ratio, and portrait/landscape orientation as layout inputs. Allow for the actual client area after system/navigation bars. Diagonal alone does not give aspect ratio; pixel dimensions alone do not give physical size.
- Ask for missing screen information when it would materially change layout choices. If proceeding without it, state the assumed target and keep the layout provisional rather than claiming usability across devices.
- Choose grid density, control spans and spacing so touch targets and text remain usable on the intended screen. Consider the interactive region, not just the artwork: rotary gestures and the halves of a multi-position switch need enough room for fingers.
- For a smaller device, simplify the panel or split controls into task-focused pages with clear navigation instead of uniformly shrinking a dense tablet design. If both phones and tablets must be supported, design around the smallest intended device or offer separate layouts with the user's agreement.
- Review at the intended physical scale when possible and seek actual-device feedback on readability, accurate taps and gestures. A desktop screenshot, matching aspect ratio or passing bounds check does not establish touch usability. Do not claim precise physical target sizes without screen/viewport measurements.

## Controls

Minimize each control's logical footprint independently of the page size. Choose the smallest practical width/height that carries its label, state and interaction, and remove unnecessary blank/decorative padding. This is particularly important for source/template decks: users drag individual controls into grids that may be much smaller than the inventory page. A 15×15 source control cannot be dropped onto a 10×10 deck; users can scale compact controls up after copying them. Simple indicator lamps should not inherit large card dimensions just because rotaries or complex displays need more space. Keep labels/artwork/actions/feedback self-contained while compacting, and recheck text sizing and artwork proportions. Operational touch usability still depends on the target device and interaction; no single fixed control span fits every control type.

Use the exact `ControlTypeName` and corresponding `ControlConfigTypeName`. For example, a button uses `EXM.MatricPro.Controls.MCButton` and `EXM.MatricPro.Controls.Config.MCButtonConfig`. Its appearance/behavior is in `Config`; events are in `ControlEvents`:

```json
{"Name": "release", "Actions": [{"ActionTypeName": "EXM.MatricPro.Actions.ActionGoToPage", "TargetPageId": "another-page-id"}]}
```

Get full templates and field metadata using `deck_tool.py catalog --control MCButton` or another catalog key. Copy defaults rather than constructing a partly specified control. `new_control` supplies the commonly omitted appearance defaults and ID.

For a native touchpad, use `new_control("MCTouchpad", ...)`: its event is `touchpad`, matching the control definition and client. The raw runtime-constructor template retains an older `valuechange` name; the helper corrects it for newly generated controls. This native touchpad is separate from the excluded Stream Deck touch-strip feature.

`FontFace: "text"` means normal text; `FontFace: "icon"` means a Material Design icon name in `Text` (for example, `mdi-microphone`). Custom FontFace values depend on fonts separately installed in MATRIC. In the inspected `deck-controls-mixin.js`, `TextSize` produces pixels as `cellSize * min(Height, Width) * TextSize / 100` when both spans are present (otherwise `cellSize * TextSize / 100`). It is relative to the control's shorter dimension, while `Padding` uses `cellSize * Padding / 100`. A 9-cell-tall square control at TextSize 10 therefore renders text at 90% of a cell, not 10%. Check the target renderer and recheck text after resizing rather than keeping a fixed size across different spans. Native alignment values include `Halign: "center"` and `Valign: "mid"`; do not substitute `middle`. Slider geometry is also percentage-based inside its control bounds.

`Config.ControlBindings` is an array of `{ "PropertyPath": "...", "VariableName": "...", "Transform": "..." }`. PropertyPath is a client-state property path, not necessarily the C# configuration property name. Reuse a verified binding or inspect the relevant MATRIC client component. Transform is an optional JavaScript function body receiving `value` and `variables`; an omitted transform binds the value directly. Do not invent built-in variable names.

## Additional calculation resources

Updated MATRIC builds support `Config.AdditionalResources` on native controls using the shared configuration base. It is a case-sensitive map of stable keys to flat deck resource filenames. Register every possible image/audio file selected by a calculation, including unavailable-state artwork. Missing/null maps behave as empty maps. Applet and iframe controls retain their separate resource systems.

```json
"AdditionalResources": {
  "unknown": "mic-unknown.svg",
  "live": "mic-live.svg",
  "muted": "mic-muted.svg"
}
```

Control property bindings receive `calculateValue(value, variables, resources)`. The third argument is a read-only snapshot of the owning control's map. Return the selected filename; normal deck resource loading resolves it. For example:

```javascript
if (typeof value !== "boolean") return resources["unknown"];
return value ? resources["muted"] : resources["live"];
```

An absent key returns `undefined`; provide a suitable fallback. Existing two-argument scripts still work. Server-variable and action calculations keep their existing signatures and do not receive this control-owned map.

Declared files appear in the computed `FileResources` index, survive save cleanup and follow copied controls/pages. If copying encounters a same-name/different-content file, MATRIC updates map values; keys and scripts remain unchanged. Do not hard-code the filenames in binding transforms or manually populate the computed `FileResources` list as a substitute. Save As and export/import preserve declared files. Removing entries makes files eligible for cleanup only when nothing else still references them.

In the editor, use **Control properties → Advanced → RESOURCES (x)**. The count is entries, not distinct files. The dialog provides Add, image Preview, Replace and Remove; Apply updates the draft and Cancel discards map edits. Rename/remove are direct operations without confirmation popups. Empty/duplicate keys and invalid filenames have inline errors. Renaming a key does not rewrite scripts. Uploaded files from canceled edits may remain until normal cleanup. The calculation dialog shows the new signature, lists insertable resource expressions and tests against the current map.

Compatibility is capability-based: the catalog records the verified implementation commit and assembly hash. Do not infer availability from deck format 3 or the skill's version. Older servers may open the deck, then discard its map and delete additional files on save. Older clients cannot evaluate scripts using `resources`. Require an updated feature-capable server and client web content; preserve an exported copy before opening in an older server. For an older target, use directly referenced static states or explicitly leave a layout unresolved rather than shipping dynamic untracked artwork.

`assets/additional-resources` is a synthetic, self-contained example with three original SVGs. Create a user BOOL variable `skill_demo_muted`, initially false, before operating it. Its button toggles only that demo variable; it controls no real microphone or OBS input. Copy the example to staging with fresh deck/page/control IDs when adapting it. The offline validator checks map shapes, keys, flat filenames and file presence; it does not execute bindings or establish native/client behavior.

## Actions and events

An action's discriminant is `ActionTypeName`, the implementation class's full name. It is not the configuration class name. The converter resolves the corresponding configuration type. Internal action IDs can differ from serialized type names: Set variable serializes as `EXM.MatricPro.Actions.ActionSetServerVariable` (singular), while its internal ID ends in `ActionSetServerVariables`. The catalog keys and event maps use serialized implementation names; `action_metadata` also accepts the old internal ID as a lookup alias. Assembly-qualified `ActionType` strings and computed `FileResources` arrays are not needed in newly authored JSON.

Names and serialization matter: buttons expose `press` and `release`; sliders expose `valuechange`, not `change`. Some actions are exclusive or single-instance for an event. Native sliders can bind native volume actions; they cannot host the excluded continuous Stream Deck slider mapping. Inspect the catalog's event map before attaching actions.

Action JSON can contain numeric enums or string enums depending on the original C# definition. The catalog's `properties.<field>.enum` gives the actual JSON representation. For instance, OBS `Command` and audio mute `Command` serialize as names. Do not replace them with an arbitrary UI label or guess an enum ordinal.

## Resources and dependencies

Page backgrounds and native control image fields refer to resource files inside the deck directory. Mobile audio uses `AudioFileName`, also bundled. PC audio uses `AudioPath`, which is a machine-specific external path. Custom fonts, custom applet installations, native drivers and plugin installations need separate setup. Do not quietly embed a local executable, credentials or an entire OBS configuration into a deck.

## Visual style preferences and reference decks

If the request leaves visual style open, offer a short optional question about the preferred look: a description, a specific existing deck or suitable installed control templates. Accept everyday descriptions such as minimal, high-contrast or realistic hardware; the user need not specify individual visual fields. Do not repeat a preference question already answered or make a style decision a prerequisite for discovery, validation or packaging. If the user delegates the choice or supplies no preference, proceed with suitable installed templates and preserve their working visual geometry unless adaptation is needed.

When an existing deck is the visual reference, inspect its actual controls and assets when available rather than inferring appearance from its title. Establish which features of its appearance to carry over when that is unclear and consequential. A style reference does not automatically select its layout, actions, feedback or control behavior; author those for the current task. If the reference cannot be accessed, identify the gap and use the available description or templates without claiming to have matched unseen artwork. Keep user-deck assets local unless redistribution is authorized, and follow the visual-only transfer rules below.

## Reusing installed control templates

When the user's MATRIC deck library is available, honor a user-selected visual reference first. Otherwise use its pre-installed template decks as a starting visual source before designing new artwork. Find them by their visible deck titles, not a hard-coded library folder or deck ID:

- For ordinary decks, inspect **Default control templates**.
- For a DCS deck, inspect **Aviation button templates** first for aviation-style skeuomorphic controls, then **Default control templates**.

When the user's deck library is available, also consider decks whose controls have no attached actions as potential visual-template sources, regardless of their titles. Treat this as a discovery hint: inspect their controls, assets, bindings and other configuration before reuse. A user-selected visual reference takes priority; other suitable candidates can supplement the installed default templates.

A design-source deck need not cover every required control type. Reuse suitable designs directly, and create missing control types using the same visual language: colors, materials, borders, typography, proportions where relevant, and normal/active-state treatment. Adapt that language to each control's native interaction and geometry; do not force button artwork onto an unsuitable slider, switch or other control. Distinguish reused designs from newly created matching designs, and author actions and feedback for the target task independently.

These decks are a convenience, not an input requirement: users may have deleted them, and the portable skill must not ship their artwork. If no suitable design source is available, use native visual configuration and the user's brief; create original artwork when it materially improves the requested look.

To reuse a design, start with a newly generated control of the appropriate catalog type and fresh ID. Transfer only the visual fields that fit the target (for example, colors, text styling, `BackgroundImage`, `DialImage`, `ButtonImage`, and state visuals) and copy each referenced normal, pressed, active, or state resource into the staged deck. Then create the target's layout, bindings and actions from its actual requirements. Never carry over the template control's `ControlEvents`, bindings, variables, control ID, navigation, or plugin-specific settings merely because its appearance is useful. Validate that every transferred resource is packaged and that the target remains complete when the page background is hidden.

Preserve a suitable template's internal geometry as the starting point, including track/thumb offsets, label placement and padding. Change it for a concrete need such as a different orientation, clipping or interaction area, then review the result against the original. Resizing or copying a control is not by itself a reason to rearrange its internals. Avoid speculative visual adjustments that add no demonstrated benefit; continue to author actions and feedback independently of template behavior.

For an existing deck, preserve all original resource files and unknown root metadata. Stream Deck action resources have separate ownership and remapping rules. The validator warns about those actions but does not certify their resource snapshots or settings. Use MATRIC's own Save As/copy/export workflow for cloning plugin-owned identities/resources.

Custom applet files have separate ownership too: an `MCCustom` container references a separately installed AppletId. Use the [custom applet workflow](custom-applets.md) to create/validate the manifest, package a `.mapl`, and check deck events/parameters with `deck_tool.py validate ... --applet /path/to/applet`. A `.deck` archive alone does not install applet files.

## Control resizing and artwork proportions

Inspect the visual construction of each control before deciding whether its aspect ratio matters. A background image depicting a keycap, bezel, circular face or other proportion-sensitive geometry can look distorted when stretched to a different rectangle. Preserve that artwork's intended proportions, select a better-fitting template or deliberately adapt the artwork when the layout needs another shape. Check normal and active states and any other image layers whose geometry depends on the control bounds.

A control without a background image, or with only a solid background color, can generally change width and height independently without image distortion. An image is not automatically proportion-sensitive either: plain textures and other stretch-tolerant decoration may resize freely. Do not require proportional resizing solely because a control came from a template or contains an image. Label fit, meaningful control shape, internal elements and usable interaction areas still need review after resizing, even when no background artwork is distorted. This applies across all applications and deck types.

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
