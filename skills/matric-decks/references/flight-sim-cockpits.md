# Flight simulator cockpit authoring

Use for cockpit decks in DCS, MSFS, X-Plane and other flight simulators. This reference adds a visual-design workflow to the existing control, layout and simulator-integration checks. Apply the user's style choice throughout; a simple shortcut panel need not become a cockpit replica. Preserve verified interactions and feedback while improving artwork.

## Establish the visual benchmark

The user's desired look and feel takes precedence. When they identify an existing deck for design guidance, inspect its actual controls, assets and assembled appearance and use it as the visual benchmark within their instructions. Do not infer its design from its title or copy its actions as visual configuration. If the reference cannot be accessed, disclose that and ask for the missing design information when it materially affects the result.

With no specified style or reference, default to skeuomorphic aircraft controls: recognizable hardware forms, materials, legends and state indications informed by the matching aircraft's photos/screenshots. Follow the existing optional style question when appearance is unspecified; do not ask again when the preference is already known. A requested flat, minimal or stylized treatment is valid and must be reviewed against that choice rather than rejected for lacking photographic realism.

Record a short design brief in staging: chosen style/reference, intended aircraft/seat, functional groups, target screen, and the visual features to retain. For a hardware-inspired design, inspect the relevant control details, not just a distant cockpit overview. Identify handle profile, grip/ribbing, bezel or guard shape, indicator windows, legend placement and materials where visible. Mark uncertain features rather than filling them with unrelated generic hardware. Search the matching aircraft instrument reference online when implementation is ambiguous; if the search does not resolve it, ask the user before implementing that interaction. Continue independent work meanwhile.

Inspect installed Aviation button templates as candidates under the template-reuse workflow. Select them for their fit to the chosen benchmark; their title or availability does not establish aircraft fidelity. An unsuitable keycap or toggle does not become suitable through a metal texture, extra screws or a cockpit label. Adapt or create missing visual forms in the same design language.

Choose the artwork technique for the visual target. Reuse suitable high-quality assets when permitted; use raster artwork or image-generation tools when available and useful for convincing hardware materials, and vector/native drawing for precise geometry and markings. Preserve editable legends and controllable state layers where practical. Do not choose simple procedural shapes merely because they are easy to generate. A change of artwork technique is useful only if the rendered control better matches the benchmark; neither raster output nor added texture proves realism.

## Prove the visual family before multiplying it

Before building the whole panel in a new visual family, build and render a representative control with its intended native interaction or applet. Choose a distinctive control that tests the design, such as a selector handle with surrounding legends, a guarded switch or a split illuminated button. Keep a side-by-side reference/render comparison in staging and actually inspect it, including normal and relevant selected/active states. Correct mismatched shapes, markings, materials and proportions before copying the approach to other controls. Keep reference images private unless redistribution is permitted. This is an authoring check; routine implementation does not require an extra user approval round.

Keep the control recognizable when adapting layout for touch. Regroup controls and enlarge touch regions or legends as needed, while preserving the requested design's identifying forms and useful local relationships. Do not flatten a depicted toggle into a circular pointer or substitute an unrelated square keycap simply because the target native type is different. Honor a deliberately simplified user style. Apply [touch-region and assembly guidance](deck-format.md#cockpit-control-groups-and-touch-regions) and keep aligned artwork on its owning controls.

For revisions, preserve successful artwork, visual configuration and resource quality when correcting behavior or bindings. Review visual changes against the previous version and the user's benchmark; redesign only where the task or a demonstrated mismatch calls for it. A fresh independent authoring test may start without the earlier implementation, but its reviewer should still compare outcomes before accepting the replacement.

## Keep applets and incomplete bindings within the design

Choose native controls by verified behavior, and skin them to the visual benchmark. When a custom applet is necessary, implement the requested control face and gesture in that same visual language. A native position-count limit does not change the requested appearance. For a hardware-inspired rotary, preserve the knob/handle, fixed legends, pointer and detented selection; a gradient circle with a dropdown and plus/minus buttons is not a substitute for those features. Such widgets can be appropriate when the user's chosen style or workflow calls for them, but must not appear merely because they are easier to implement.

Missing command values or feedback mappings are integration gaps. If the user agrees to defer them, complete the artwork and any verified local interaction while leaving simulator bindings unresolved. Clearly distinguish local state from cockpit state. Use a restrained status cue and delivery notes; do not replace the control face with large diagnostic text, raw indexes or a developer interface. Preserve the reference legends that are verified; identify unverified labels in the notes rather than presenting guesses as aircraft facts.

Review the actual rendered applet, not just a schematic of its intended appearance. Browser evidence establishes that rendering only; it does not prove MATRIC host behavior. Follow the existing manifest, padding/background, gesture and packaging requirements independently.

## Visual acceptance evidence

Before calling the visual design complete, record concrete findings in staging:

| Review | Evidence and reasons to revise |
| --- | --- |
| Appearance | A representative control close-up and complete page render compared with the chosen visual benchmark. Check shapes, legends, materials, indicators and consistency across native controls/applets. Generic replacement hardware or a different applet design language requires revision unless requested. |
| State artwork | Inspect normal, selected/active and unavailable/local-only presentations where applicable. Labels, pointer and indicator windows must remain legible and consistent with the chosen design. Review artwork separately from whether the underlying feedback mapping works. |
| Layout and touch | Inspect grouping, clipping, overlaps, proportions, label readability and full touch regions at target and differing proportions, including with the page background hidden. State remaining physical-device uncertainty. |

Use actual client renders when available and label approximations clearly. When suitable rendering is unavailable, deliver the authorized package with visual review outstanding; do not assert that it passed. A renderer comparison should identify specific matches and differences rather than merely say "looks realistic" or "reviewed." Fix observed mismatches or resolve a consequential design choice with the user. Continue the existing interaction/integration checks independently; passing structural validation, event tests or packaging does not override a failed appearance review.

Deliver the visual result alongside the package and brief setup/limits. Describe a mapping-deferred deck as such. Do not claim this workflow guarantees visual quality or that a static validator can judge resemblance; it supplies evidence on which to accept or revise the result.
