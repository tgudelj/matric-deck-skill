# Setup, handover and revision reports

Use `scripts/workflow_tool.py` to bring discovery results into a setup report, explain a delivered deck, or check a revision. It uses only standard-library Python and the other installed helpers. Default output is Markdown; `--format json` provides structured data for follow-up commands. `--output` creates a new file and refuses overwrites. Keep reports and evidence outside staged deck folders: every deck asset must remain flat beside `deck2.json`, and authoring reports do not belong in the importable package.

These commands do not import decks, send inputs, acquire a joystick, execute JavaScript or operate a live library. Only an explicitly supplied OBS endpoint causes network access, using the existing read-only discovery client. Reading files or querying OBS does not establish that MATRIC integrations or target applications work.

## Write for the person using the deck

Markdown reports use everyday wording, with the result and next step first. Checks appear as "Checked," "Confirmed by you," "Please confirm" or "Needs fixing." A check without notes is "Not checked here yet"; this means it hasn't been covered here, not that it failed or could never have been tried elsewhere. Checks supplied through review notes say where the result came from. JSON keeps the existing status codes and field names for follow-up tools.

Use the same tone in the chat summary and authored control/review notes:

| Avoid | Prefer |
| --- | --- |
| Visual review has no recorded evidence. | The layout hasn't been checked here yet. Look over the labels and spacing next. |
| Structural validation passed. | The deck files passed their checks. |
| Input sources require review. | Your saved settings have changed. Check the deck's bindings against them. |
| Feedback is configured but unverified. | The display is linked. Check that it matches the app. |

Use each example only when it matches the result. For a failed check, say what needs fixing; for a missing check, say what to try next. Keep visual checks, importing into MATRIC, trying the physical device and using the target app separate. Technical IDs, fingerprints, discovery JSON and changed field paths remain available in the report's expandable Technical details section. User-authored notes are displayed as supplied, so write them in this tone too.

## Check the setup

Run the relevant setup check when establishing a new authoring context or when its configuration changes. Use explicit paths; profile discovery lists candidates but never selects an active profile. Choose `desktop` for ordinary shortcuts and `game` for the supported input-profile readers. The `dcs` target checks the DCS-BIOS/DBMM authoring path; a keyboard-only DCS panel can use the desktop path and separately verified shortcuts.

```text
python scripts/workflow_tool.py setup --format json --output /delivery/setup.json
python scripts/workflow_tool.py setup --target obs --obs-collection /inputs/collection.json
python scripts/workflow_tool.py setup --target obs --obs-snapshot /inputs/obs-live.json
python scripts/workflow_tool.py setup --target obs --obs-url ws://127.0.0.1:4455 --format json --output /delivery/obs-setup.json
python scripts/workflow_tool.py setup --target game --game xplane --discover-root /inputs/profiles
python scripts/workflow_tool.py setup --target game --game elite --profile /inputs/Selected.binds --require-action LandingGearToggle --format json --output /delivery/game-setup.json
python scripts/workflow_tool.py setup --target dcs --dcs-definitions /inputs/doc/json --aircraft F-16C_50 --format json --output /delivery/dcs-setup.json
```

Supply a live OBS password through `OBS_WEBSOCKET_PASSWORD`, or name another environment variable with `--obs-password-env NAME`. Never put a password in the URL, command line or report. For private interactive prompting, first use `obs_live.py --ask-password --output ...`, then pass its snapshot. Live discovery has a 30-second snapshot budget; optional OBS request failures remain visible as warnings. A saved snapshot describes its capture time, not the current connection.

Game options reuse `game_bindings.py`: repeat `--profile`, use `--device-map` for an explicitly reviewed virtual-device mapping, and `--require-action` to flag missing assignments. Profile/context conflicts remain review items. Supported readers and their exclusions are documented in [application input discovery](application-inputs.md). DCS checks load the selected module/alias and fingerprint its JSON files without configuring exporters or proving aircraft behavior.

Setup statuses have deliberately different meanings:

| Status | Meaning |
| --- | --- |
| `checked` | The helper observed an authoring fact, such as a parseable saved profile. |
| `user_confirmed` | The user explicitly confirmed a prerequisite; the helper did not test it. |
| `needs_confirmation` | Information or setup remains to be established. Offline authoring can continue with disclosed limits when authorized. |
| `blocked` | A concrete check failed, such as unreadable definitions, missing required assignments or Python older than 3.11. |

Use `--active-confirmed` only when the selected game profiles/layers are actually confirmed. `--confirm` records explicit prerequisite confirmations and accepts `matric`, `obs`, `dcs`, `dcs_bios`, `dbmm` and `vjoy`. For example, `--confirm obs` means the user confirmed MATRIC's OBS integration; discovering an OBS collection alone does not justify it. No global “ready” label is inferred. Setup checks supplement the existing OBS design defaults and cockpit reference research; they do not replace either workflow.

## Deliver a handover

After validation and packaging, generate a handover from the final `.deck` or staged folder. Include relevant applet packages, discovery reports and input sources:

```text
python scripts/workflow_tool.py handover /delivery/Panel.deck --setup-report /delivery/game-setup.json --profile /inputs/Selected.binds --format json --output /delivery/handover.json
python scripts/workflow_tool.py handover /delivery/Panel.deck --setup-report /delivery/game-setup.json --profile /inputs/Selected.binds --output /delivery/handover.md
python scripts/workflow_tool.py handover /delivery/Cockpit.deck --dcs-definitions /inputs/doc/json --aircraft F-16C_50 --output /delivery/cockpit-handover.md
python scripts/workflow_tool.py handover /delivery/Widget.deck --applet /delivery/Widget.mapl --output /delivery/widget-handover.md
```

The report describes each control's declared actions, requirements, variable references, documented input source, setup steps and unresolved work. Common shortcuts, OBS operations, page navigation and vJoy targets receive readable summaries. Text bodies, HTTP URLs/headers/bodies and opaque plugin settings are not copied. Generic actions receive catalog descriptions; supply a precise purpose when the configuration alone cannot establish intent. Variables are reported as configured references, not verified live feedback. Applet variable parameters are inspected when manifests are supplied; arbitrary applet code and calculated variable access are not analyzed.

The helper checks the deck files. Layout review, importing into MATRIC, trying your device and using the target app start as "Not checked here yet" (`not_recorded` in JSON). To add the results of checks you actually performed, first get the final payload fingerprint from a JSON handover, then create an evidence file outside the staged folder:

```json
{
  "schema_version": 1,
  "payload_sha256": "REPLACE_WITH_FINAL_HANDOVER_PAYLOAD_SHA256",
  "checks": {
    "visual_review": {
      "status": "passed",
      "notes": "Compared the offline preview with the chosen reference at the intended proportions. It still needs trying on the tablet."
    }
  },
  "controls": {
    "REPLACE_WITH_CONTROL_ID": {
      "purpose": "Switch to the selected OBS scene",
      "input_source": "Scene name from the user's active-collection discovery",
      "setup": ["Configure MATRIC's OBS integration"],
      "unresolved": ["Try scene switching and check the active-scene highlight with OBS running"]
    }
  }
}
```

This is an illustrative schema, not evidence that any review passed. Replace its values with actual findings. Supported check names are `visual_review`, `native_import`, `physical_device` and `live_application`; each requires nonempty notes and `passed`, `failed` or `not_checked`. Control notes accept `purpose`, `input_source`, `setup` and `unresolved`, keyed by existing control ID. Do not infer passes from generated artwork, packaging or this example.

Pass the evidence with `handover ... --evidence /delivery/evidence.json`. If applets are supplied, copy the handover's `applet_sha256` map into the evidence too. Evidence must match every deck payload file and every explicitly supplied applet payload; changed bytes invalidate it. The helper labels these claims as recorded evidence, never as tests it performed. Evidence freshness does not establish the truth or quality of the recorded review, and it does not capture changes in the running application.

Input and applet sources receive SHA-256 fingerprints. Setup sources are rechecked at handover time, and changed or unavailable sources are shown. A stale source supplied both through setup and as a current `--profile` is rejected so conflicting snapshots are not silently merged. Source paths, scene names and user-authored notes can contain private information: keep reports local or review them before sharing. Credentials never belong in notes.

## Compare a revision

Keep the exported baseline and its handover JSON. Compare the final revision before delivering an update, particularly for changes requested only to layout or appearance:

```text
python scripts/workflow_tool.py compare /delivery/Before.deck /delivery/After.deck --baseline-report /delivery/before-handover.json --output /delivery/changes.md
python scripts/workflow_tool.py compare /delivery/Before.deck /delivery/After.deck --baseline-report /delivery/before-handover.json --presentation-only --format json --output /delivery/changes.json
```

Matching uses stable deck/page/control IDs, never similar labels. The comparison reports added/removed controls, page/control order, movement between pages and changed JSON field paths. It separates known layout/appearance/metadata changes from actions, feedback, dependencies and unknown fields. Action order, timing, control names, scripts, interaction configuration and opaque data are preserved in the comparison; their raw values are omitted from reports. A deck identity change is explicit because it affects import/update behavior.

All resource bytes are compared, including files absent from direct image references. Known native raster artwork can be classified as presentation; SVG, audio, dynamic resources and unrecognized assets conservatively require review. The original inputs are never modified. JSON formatting/key order alone is not a semantic field change.

With `--baseline-report`, the report must match the exact before payload. Previously recorded profile, definition and applet paths are re-read and reported as `unchanged`, `changed` or `unavailable`. Applet directory fingerprints also detect newly added files. Relocated sources are unavailable until explicitly re-established; there is no automatic search or rebinding. This catches source drift, but does not interpret changed bindings or semantically compare applet code. Without a baseline report, source drift is not checked.

`--presentation-only` returns exit 1 if behavior, feedback, dependency, structural, unknown-field or recorded-source changes need review. It returns 0 for unchanged decks and known presentation edits. The result is a review aid, not proof of behavioral equivalence: resizing, reordering, artwork, CSS and screen proportions can affect usability, and arbitrary scripts may depend on changed presentation values. Preserve a baseline and perform the relevant target-device/application checks.

All commands return nonzero for invalid input or output errors. Setup also returns 1 for blocked checks. Handover writes its report but returns 1 for recorded failed reviews, blocked setup checks or DCS audit errors. Missing live-test evidence and unconfirmed prerequisites stay visible without preventing a disclosed offline delivery.
