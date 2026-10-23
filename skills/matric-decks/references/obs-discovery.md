# Discover OBS independently of MATRIC

Use saved collection files first when the task needs scene/source names and structure. This works with OBS closed, covers inactive collections, and requires neither a MATRIC connection nor a WebSocket client. For current runtime state, an assistant can connect directly to OBS with a separate client.

## Saved collections

Prefer a JSON exported with OBS **Scene Collection → Export**, or an explicitly identified local collection file. Common normal-install locations are:

| Platform | Scene collection directory |
| --- | --- |
| Windows | `%APPDATA%\obs-studio\basic\scenes` |
| macOS | `~/Library/Application Support/obs-studio/basic/scenes` |
| Linux | `$XDG_CONFIG_HOME/obs-studio/basic/scenes`, normally `~/.config/obs-studio/basic/scenes` |

Portable installations and customized config locations differ. Do not assume that the filename equals the collection's display name. If OBS is saving the file while it is read, retry or use an exported snapshot. Never edit the source collection during discovery.

```powershell
python scripts/obs_inventory.py "$env:APPDATA\obs-studio\basic\scenes" --output obs-inventory.json
```

The helper accepts a single collection JSON or a directory of `*.json` collections. It emits exact names, UUIDs, scene order, scene/group membership, item IDs, saved visibility/locks, source kinds, filters, transitions, audio settings and shortcut bindings when present. It omits source settings such as browser URLs and media paths. Its output is still user configuration: share only the information needed for the task.

Interpret its output as follows:

- `collection` comes from the JSON `name`; `scene_order` gives the saved scene ordering.
- `containers` represents scenes and groups. Resolve item references by UUID, falling back to name for older files. A scene item is an instance of a source: the same source can appear in several scenes or groups, with different visibility and item IDs. A nested scene is a reference to another container. Follow this graph with a visited set rather than assuming a flat source list.
- `sources` includes global audio devices stored outside the ordinary sources array. Filters belong to their parent source. Source kind identifiers are OBS/plugin types, not MATRIC action names.
- `hotkeys` preserves recorded OBS keys and modifier flags; an empty list means no saved binding. OBS key names need an explicit translation to MATRIC/Windows key codes. Do not treat a hotkey identifier as its keyboard binding.
- `saved_*` fields are snapshots. They do not establish the currently running scene, whether an input is available, or whether streaming/recording is active. Saved volume is not a live meter reading.

Collections contain scenes, sources and global audio; output configuration belongs to OBS profiles. The helper intentionally does not read stream service credentials or profile files. See [OBS scene collections](https://obsproject.com/kb/scene-collections) and the [collection implementation](https://github.com/obsproject/obs-studio/blob/master/frontend/widgets/OBSBasic_SceneCollections.cpp). Saved JSON is an implementation format and can evolve; inspect warnings and check unfamiliar versions before generating bindings.

## Optional direct live discovery

OBS 28+ includes obs-websocket. Obtain the enabled endpoint and credentials from the user's OBS **Tools → WebSocket Server Settings**; the usual port is 4455. Use an available WebSocket client independently of MATRIC. Do not install or start a new server just for file discovery. See [the official setup guide](https://github.com/obsproject/obs-websocket#using-obs-websocket).

For the v5 JSON handshake, wait for `Hello` (`op: 0`). Send `Identify` (`op: 1`) with `rpcVersion: 1`, `eventSubscriptions: 0`, and authentication when required; wait for `Identified` (`op: 2`). Authentication is `base64(SHA256(secret + challenge))`, where `secret = base64(SHA256(password + salt))`; hash UTF-8 input to binary digests. Keep credentials outside deck files and reports. [Official authentication and handshake](https://github.com/obsproject/obs-websocket/blob/master/docs/docs/partials/introduction.md).

Query `GetVersion` first and check `availableRequests`. Requests use `op: 6` and `d: {requestType, requestId, requestData}`; match `op: 7` responses by `requestId` and check `requestStatus.result` before using data.

| Discovery | Requests / request fields |
| --- | --- |
| Collection names | `GetSceneCollectionList` |
| Current collection's scenes | `GetSceneList` |
| Scene membership | `GetSceneItemList` with `sceneName` |
| Group membership | `GetGroupSceneItemList` with group `sceneName` |
| Inputs | `GetInputList` |
| Source filters | `GetSourceFilterList` with `sourceName` |
| Transitions | `GetSceneTransitionList` |
| Audio state | `GetInputMute`, `GetInputVolume` with `inputName` |
| Studio/program/preview state | `GetStudioModeEnabled`, `GetCurrentProgramScene`, `GetCurrentPreviewScene` |
| Hotkey identifiers | `GetHotkeyList` (identifiers, not assigned shortcuts) |

Traverse nested scenes/groups with a visited set; retain parent container and item ID. Inactive collections require saved files: switching collections changes OBS. Handle request failures, disconnection and absent preview mode explicitly. Discovery should not switch scenes/collections or start outputs. [Official request reference](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md).

## Map the inventory to MATRIC

Use the exact collection, scene and source names with the native action recipes in [action-recipes.md](action-recipes.md). Native MATRIC OBS actions still need MATRIC's OBS integration configured for execution; only discovery is independent. Alternatively, use confirmed OBS keyboard shortcuts with MATRIC hotkey actions, accounting for focus/global-hotkey behavior. Discovery alone does not create shortcuts or make an unassigned shortcut work.

Do not generate source visibility controls for ambiguous repeated/grouped items unless the selected MATRIC action can identify the intended target. Discovery can expose more detail than MATRIC's action configuration can express. Do not invent fields or silently flatten these distinctions.
