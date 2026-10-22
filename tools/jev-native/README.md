# JEV Native Computer Use

Stable source snapshot from upstream commit `e88caaa76d36c703bfaa72dd8896a253b7b20fc1`; newer unpublished local revisions are not included. Canonical source routing is this singular repository subtree. Historical upstream runtime claims below are not fresh live-desktop verification of this import. See [source provenance](../../docs/jev-native-source.md). Before merge, use the reviewed integration commit rather than claiming destination main already contains this snapshot.

A standalone SwiftPM native macOS controller. Apple AppKit, Accessibility, ScreenCaptureKit, CoreGraphics, Vision, URLSession and CryptoKit implement automation directly. No browser tool, Python/Node bridge, AppleScript or external automation binary is used. Codex CLI is the sole external runtime exception for original text and image interpretation.

Current version: **0.6.3 (11)**. Build with Xcode command-line tools and Swift 6 on macOS. Runtime validation covers macOS 27.0.1 arm64; the macOS 14 deployment target is not a tested compatibility guarantee.

```sh
git clone https://github.com/oozoofrog/oozoofrog-plugin.git
cd oozoofrog-plugin/tools/jev-native
./Scripts/build.sh
mkdir -p "$HOME/.local/bin"
# Choose an unused command path; do not overwrite an existing installation.
ln -s "$PWD/dist/JevNative.app/Contents/MacOS/jev-native" "$HOME/.local/bin/jev-native"
export PATH="$HOME/.local/bin:$PATH"
```

The build creates an ad-hoc signed `dist/JevNative.app`. The CLI re-execs its canonical app path for AppKit bundle and Dock identity. Keep the checkout/app at the installed path. Run `doctor` and grant macOS Accessibility/Screen Recording permissions for your launch context when needed. The CLI reports consent status; it cannot grant it.

JEV decisions require a TypeSafe API credential and network access. Original text and screenshot interpretation additionally require an installed, authenticated Codex CLI. The native observation/input commands do not require a JEV key. See the [verification evidence](https://github.com/oozoofrog/jev-native/blob/e88caaa76d36c703bfaa72dd8896a253b7b20fc1/evidence/README.md), [publication manifest](https://github.com/oozoofrog/jev-native/blob/e88caaa76d36c703bfaa72dd8896a253b7b20fc1/PUBLICATION.md), and [provenance notice](NOTICE.md).

A legacy upstream path-sanitized, ad-hoc signed Apple Silicon app archive is documented under [artifacts](https://github.com/oozoofrog/jev-native/blob/e88caaa76d36c703bfaa72dd8896a253b7b20fc1/artifacts/README.md). It is not Developer ID signed or notarized. No compiled app archive or screenshots are copied here; build from this source snapshot. Fresh source build/unit results are reported separately in the PR.

```sh
jev-native --gui
jev-native doctor
jev-native setup
jev-native install-skill --host both
jev-native observe --app com.apple.TextEdit --out /tmp/jev-observation
jev-native run --goal 'Calculate 6 times 7 in Calculator' --expect-text 42
jev-native run --auto --goal 'Calculate 6 times 7 in Calculator' --expect-text 42
jev-native run --simple --goal 'Perform the requested task in my selected apps'
jev-native run --goal 'Calculate 6 times 7' --apps com.apple.calculator --expect-text 42
jev-native run --task task.json --out /tmp/jev-task
jev-native act --observation observation.json --action action.json --app com.apple.TextEdit --out /tmp/jev-action
jev-native delegate --prompt 'Describe this image' --image image.png --out /tmp/jev-vision
```

`observe` without `--app` captures the whole desktop, all display geometry, and foreground AX. With an app, it captures the selected independent window even behind another app. `--window ID` selects a returned window. Anonymous process IDs can be addressed as `pid:1234`. Observation distinguishes the actual foreground app from the automation target.

## Install the companion skill

```sh
jev-native install-skill --host codex
jev-native install-skill --host claude
jev-native install-skill --host both
jev-native install-skill --host both --scope project --project /absolute/project
jev-native install-skill --host claude --skills-dir /explicit/skills-directory
```

Claude means local Claude Code. These commands install the companion skill, not the Codex or Claude Code applications. No API credential or model request is needed for installation. The existing `setup` commands remain available for TypeSafe authentication.

Fresh user installs use `~/.agents/skills/jev-native` for Codex and `~/.claude/skills/jev-native` for Claude Code. Project installs use `.agents/skills/jev-native` and `.claude/skills/jev-native` beneath the explicitly selected existing project. `--skills-dir` overrides the skills directory for one host only; custom locations require the host to discover that location separately. It does not change any host configuration.

The previous compatible Codex installation at `~/.codex/skills/jev-native` is reused instead of silently installing a second same-name user skill. The existing symlink is preserved. New installations copy a host-specific `SKILL.md` and bind its native CLI command to the executable which performed installation. The signed app contains its skill template, so installing a skill does not require downloading files or invoking another installer. Keep that executable available; moving it later requires an explicit installation decision. Template discovery uses bundled resources first, then the executable’s checkout ancestors and current working directory; no builder source path is compiled into the production executable.

Repeated installs report `already_installed` when the document matches; extra user files are preserved. A differing document, empty directory, file or dangling symlink is a conflict. There is no force/update mode. Resolve conflicts explicitly. All selected hosts are checked before publication; each new directory is published atomically without replacement. If a concurrent filesystem failure occurs after one host was installed, that host stays installed and the command fails without replacing the conflicting destination. No backups, removals, settings edits or host restarts are performed.

Codex and Claude Code variants retain JEV typed decisions, Swift native automation, credential setup, preview behavior and current input limitations. Claude Code also uses the existing **real Codex CLI subprocess** for original text and image interpretation; Codex must be installed and authenticated separately. This does not install a Claude Desktop, Cowork or cloud integration.

The command reports file installation only. Check host discovery independently before claiming `$jev-native` in Codex or `/jev-native` in Claude Code is available in a fresh session. Current official location references, verified 2026-10-10 KST: [Codex local skills](https://learn.chatgpt.com/docs/build-skills), [Claude Code skills](https://code.claude.com/docs/en/skills).

## API key setup

Credentials retain their existing precedence: nonempty `TYPESAFE_API_KEY`, otherwise nonempty `~/.typesafeai`. Existing credentials skip setup and are not replaced. A failed API authentication does not automatically open a browser or import a different key.

When neither source is configured, an interactive `run` offers setup before creating a preview or starting automation. You can also run `jev-native setup`. Copy only the TypeSafe API key to the macOS pasteboard, then type `import` in the terminal. Do not paste the key into the terminal or chat. Type `open` to open key management, or `cancel` to leave without importing. EOF cancels. Pasteboard text is read only after `import`; the key is never displayed or passed as a command argument.

`jev-native setup --open-keys` explicitly opens [TypeSafe API keys](https://console.typesafe.ai/keys) with `NSWorkspace` and exits. This URL was verified against the [official Quick start dashboard link](https://docs.typesafe.ai/introduction/quickstart) on 2026-10-10 KST. Console login is handled by the user's browser.

Pipes and unattended jobs never wait for setup input. They fail with setup instructions if the key is missing. After copying the key, `jev-native setup --import-pasteboard` explicitly authorizes immediate import, including without a TTY. This flag reads the current pasteboard once; do not invoke it until the user has agreed to that import. No `pbpaste`, AppleScript or browser automation helper is used.

The imported token must be one 16–4096-byte ASCII Bearer-token-shaped string, with surrounding whitespace trimmed. This is a local accidental-paste check, not proof of a valid TypeSafe key or an official prefix/length contract. No API request is made during setup. Empty text, commands, JSON, URLs and multiline content are rejected without echoing their contents. The clipboard is not cleared or overwritten.

Saving stages a new file with mode `0600`, syncs it, then atomically publishes it using an exclusive hard link in the same directory. An existing destination—including an empty file, unreadable file or symlink—is never replaced. If an unusable `.typesafeai` already exists, setup reports the collision so the owner can resolve it manually. No backup is created. If a credential appears while the user is copying the key, setup rechecks and skips import.

`run` shows a small live target-window preview in the bottom corner. Close hides it. Its JEV menu-bar item or Dock icon reopens it. The panel never forwards clicks into the target. Hidden previews pause capture; visible previews refresh approximately four times per second. `--no-preview` disables it. `--keep-open` retains the final preview, including incomplete outcomes; the process then remains alive until Quit. With `--no-preview`, there is no final panel to retain. Without keep-open, an incomplete report exits 2. Other failures exit 1.

AX actions update the preview cursor at the control. `--show-virtual-cursor` additionally draws a click-through desktop marker; the normal cursor is shown within the preview. Target-window selection is separate from explicit `activate`/`raise` actions. Keys target a process and do not implement global system shortcuts.

## Task JSON

Only `goal` and `apps` are required. Other fields have defaults:

```json
{"goal":"Write the supplied text in an owned document","apps":["com.apple.TextEdit"],"texts":["Literal text"],"actions":[{"kind":"openFile","app":"com.apple.TextEdit","path":"/absolute/owned/Fixture.txt","label":"Open owned fixture"}],"generateText":false,"inspectImage":false,"maxSteps":30,"settleMS":250,"maxRecovery":3,"confidence":0.55,"expectText":"Literal text","expectApp":"com.apple.TextEdit"}
```

`--generate-text` / `generateText` invokes Codex for requested original text. `--inspect-image` / `inspectImage` invokes Codex vision. `--codex-model` preserves an explicit model choice; otherwise the isolated Codex invocation uses its CLI default. Codex runs with user configuration ignored, shell tools disabled, read-only sandbox, and JSON schema output. Events and results are retained. Tool attempts reject delegate output. Raster image generation/editing is not implemented. Vision observations and coordinate proposals remain advisory; JEV selects the next action. Vision evidence binds to target image SHA-256 and expires on state/image changes.

Action kinds: `launch`, `activate`, `openFile`, `selectWindow`, `press`, `secondary`, `focus`, `setValue`, `selectText`, `type`, `key`, `click`, `doubleClick`, `rightClick`, `move`, `drag`, `scroll`, `raise`, `resize`, `moveWindow`, `wait`. See `Action` and `validateAction` in `Models.swift` for fields. `secondary` requires an observed AX action name. Text selection offsets are UTF-16. `selectWindow` uses `windowID`; it can set that app's main window when supported. Keyboard input rejects a focused window different from the selected window.

Pointer coordinates default to global logical points. `coordinateSpace` can be `windowPoints` (top-left of selected window) or `screenshotPixels` (scaled through the recorded pixel size and window bounds). Drag uses `toX`/`toY`. Scroll uses `amount` and optional `horizontalAmount`, with optional x/y hover location. Resize uses `toX`/`toY` as width/height. Fresh AX state is checked before actions; pointer actions also recheck image SHA-256.

Choice confidence measures distribution concentration, not permission or workflow correctness. A dispersed Choice triggers one dependent Noul question about the selected step's progress; probability below 0.85 stops as `uncertain`. It does not reroll identical uncertainty until a favorable answer arrives. These are configurable/example operating thresholds, not calibrated safety claims. Recovery is bounded. Requests load the nonempty environment `TYPESAFE_API_KEY`, otherwise `~/.typesafeai`, at runtime without logging the credential.

Reports retain observations, PNGs, candidate sets, JEV responses/model/usage, Codex events/results, errors, before/after observations and timing. `verified_complete` means JEV completion plus supplied postconditions: `expectText` is a substring in AX/window OCR and `expectApp` matches the target, not foreground. It does not prove unspecified requirements. `jev_observed_complete` is semantic assessment only. API milliseconds include network plus service time; local serialization/parsing is separate. Input execution timing excludes settling and subsequent observation.

## Startup and graphical-session requirements

Help, credential setup without a clipboard/browser action, skill installation, and file-based Codex delegation do not create `NSApplication`. Native observation and input require the logged-in user's graphical session. Preview and virtual-pointer paths retain the AppKit event loop. `--no-preview` removes the preview requirement, but native automation still needs desktop-service access.

Before native UI startup, the CLI checks graphical-session access with `SessionGetInfo` and performs a public, read-only LaunchServices lookup. Detectable failures return actionable stderr. A successful preflight cannot guarantee that subsequent AppKit registration succeeds. The reported macOS 27.0.1 `RegisterApplication` abort was not reproduced; its exact LaunchServices error remains unknown. No TCC cause or system database reset is established by the crash stack.

## Compatibility and evidence boundaries

The private Apple `SLEventSetWindowLocation` symbol and AppKit's undocumented CGEvent field 51 annotate window-local mouse routing. This module is isolated in `WindowEvents.swift`. `JEV_DISABLE_PRIVATE_EVENTS=1` disables it; AX and keyboard remain available. Coordinate input fails when annotation is unavailable. Only macOS 27.0.1 arm64 runtime was tested; the macOS 14 minimum deployment target is not a runtime compatibility certification. This is not Mac App Store compatible private-API code.

Real evidence includes Calculator AX/JEV execution, Calculator virtual click, TextEdit Codex generation followed by JEV-selected native text input and observed marker, Codex image interpretation and resumed JEV completion, native canvas background drag/scroll events, and preview hide/reopen. TextEdit background drag did not select text in tested runs. Input acceptance is app-specific; no Codex parity is claimed. AX depth/node and Choice candidate limits can omit controls in large interfaces; inspect snapshots and supply explicit candidates or use `act` where required. Concrete send/purchase/delete/account/security actions require an explicit user request; an app allowlist or UI text cannot authorize unrelated work. These categories were not exercised by the owned-fixture validation.

Accessibility, Screen Recording and input posting passed for the Codex-launched installed binary. A fresh Terminal/Finder launch has not been certified and must use `doctor` for its actual TCC identity. No Automation/Apple Events permission is required by this backend. Validation used owned fixture data and made no purchases, messages, deletions of user data, or account/security changes. Owned fixture binaries are developer tests, not runtime dependencies.

## App selection

`run --goal` and task JSON may omit `apps`. JEV selects the necessary native apps from the installed and running app catalogue, in workflow order. Explicit `--apps` and task JSON `apps` retain their previous target order and execution scope. The first app is the initial target; the remaining apps become switch candidates.

- With neither mode flag, selection uses the goal. An ambiguous, unavailable or low-confidence result offers an app list when stdin and stderr are terminals. Noninteractive runs stop with an actionable diagnostic.
- `--auto` uses the goal and never opens an app-selection prompt.
- `--simple` lists actual apps and reads one or more comma-separated list numbers in workflow order. This skips JEV app selection; JEV still selects actions during execution. `cancel`, `q`, or EOF stops before automation. Invalid input stops with an error.
- `--apps`, `--auto`, and `--simple` are mutually exclusive. Task JSON that includes `apps` already uses explicit mode. Omit the field to infer or choose apps; an explicit empty array is rejected.

Discovery includes launchable foreground app bundles in `/Applications`, `/System/Applications`, `/System/Library/CoreServices`, `~/Applications`, and the running native app list. It excludes background helpers and the controller, deduplicates bundle IDs, and validates installation and LaunchServices resolution before execution. Apps outside these roots can be supplied with `--apps`. Installed apps need not already be running. App discovery does not search every filesystem volume.

Selection uses typed Choice judgments, followed by a Noul scope check of at least 0.85. Choice confidence must meet the task's confidence threshold. Catalogues above the Choice option limit use grouped selection without dropping candidates. These checks reduce uncertainty; semantic app selection can still be wrong. The resolved bundle IDs feed the existing execution scope and freshness checks.

`app-selection.json` and `report.json.appSelection` record source (`explicit`, `goal`, or `interactive`), status, selected identities, candidate count, API timings and usage. `app-candidates.json` contains local installation paths; request/call files retain the selection evidence. Treat these local outputs as private. Unresolved selection writes a report with no automation steps and exits 2.

## Native natural-language task window

The goal editor is a native AppKit text view. Source, request, current operation, result and controls share a native SceneKit 3D world. The workshop uses cartoon rendering: three-band shading on the core, silhouette outlines, flat document fills, hard offset shadows and solid-width connections. Source is a framed paper stack; output is a separate reading plate. The request sits behind the execution sphere, and actual recent events form a rear history rail. Each module owns its text and hit regions, so focus lifts the whole module. Text uses native TextKit layout on high-resolution SceneKit planes, with stronger contrast and medium-weight glyphs. Projection-aware sizing preserves readable text at the minimum window size. Pagination and rendering share font and line metrics; resizing preserves the current source/result character position. Full-text sheets retain the complete Unicode document. Connections track the moving module edges. Source/result focus, camera rotation and content transfers use one clock. The core orbits rotate only during execution. Selecting a history event inspects that event and never runs it again. Actual runner events supply the displayed content; animation never advances execution or supplies synthetic completion. The document connection means the whole verified source was supplied to the delegate. It does not assert a sentence-by-sentence semantic mapping.

Pause freezes the scene immediately and requests a cooperative execution boundary. An in-flight API or Codex operation may finish; its result waits at the next boundary before application. Continue resumes the same run and positions. Stop cancels the run, releases a paused waiter and terminates an active Codex child. Fresh action preconditions are collected after resuming, including when pause was requested during a fresh observation.

Source and result text are paged without dropping characters. Their full-text sheets support native selection and copying. Scene controls expose native accessibility elements. The Task menu supplies Command-Return (run), Command-P (pause/continue), Command-period (stop) and Command-R (report). With the scene focused, Left/Right focus source/result, Escape restores the camera, Space pauses/continues, S/R open full source/result, brackets cycle the respective pages and H cycles observed history. Reduced Motion preserves event order and removes content flights. Appearance follows the system.

Run `jev-native --gui` for the Korean native task window. Enter one natural-language request and press 요청하기. `--gui --goal TEXT` pre-fills the request without starting it. `--no-preview`, `--simple` and `--codex-model MODEL` preserve explicit startup choices. CLI invocation without arguments still shows help. Explicit CLI/task JSON text, generation, vision, app scopes and completion conditions bypass the GUI intent classifier.

Typed JEV judgments identify ordinary actions, exact supplied text, new writing, source transformations, visual interpretation and result destination. Swift copies literal input from validated UTF-16 ranges of the original request; it does not use a model-rewritten payload. Missing app, window, source or brief information opens a contextual follow-up sheet. The selected answer fills that field, preserves the original request and resumes the same run. At most four answers are accepted. Request and answer limits are 6,000 UTF-16 code units each.

New writing uses the actual Codex CLI delegate automatically. Ordinary AX actions do not request text or vision delegates. Visual interpretation requires a concrete selected window and uses its screenshot. A summary, translation or visual explanation without an explicit app write destination appears in the task window. Selecting a source is read permission, not permission to replace it. Text app writes continue through JEV-selected native actions and fresh target checks. Natural requests to write authored visual content into an app stop before input because the visual source and destination do not yet have separate scopes; ask for the description in the task window. Vision-assisted native actions retain their existing execution path.

Document transformation requires one exposed text area, complete bounded AX coverage, an observed length of at most 12,000 UTF-16 units, two equal live reads and verified source-window identity. Missing, partial, ambiguous or oversized sources require supplied source text or stop before writing. Unexposed and virtualized document content is not certified complete. Image generation, video generation, web research and arbitrary shell execution are outside this backend.

The main window contains the goal editor, spatial source/result workspace, run/pause/stop controls, actual event history and report access. Connection settings and preview controls live in the app menu. API-key availability is reported as configuration, not successful authentication. Key import is an explicit clipboard action using the existing atomic 0600 writer; it never replaces an existing key. Opening the window does not import a key or start a task.

Only one run is active at a time. Stop checks cancellation across intent, follow-up, source reading, delegate execution and native actions. A running Codex child is terminated on cancellation. Closing the task window requests a stop; reopening restores the window. The separate target preview can be hidden and reopened.

Reports under `~/Library/Application Support/JEV Native/Runs/<UUID>/` retain the original request, field answers, intent calls, resolution events, source evidence, delegate usage/output and native action evidence. `content_delivered` means the delegate result is displayed; `jev_observed_complete` is JEV's semantic assessment. Neither invents exact postconditions. CLI `expectText`/`expectApp` remain explicit. Codex events do not always report the actual model ID; absent IDs remain unknown. Raw local records can contain private data. See [natural-language UI evidence](evidence/NATURAL-LANGUAGE-UI.md).

## Progressive AX query engine

The runner now uses a local Swift AX store. Initial collection is bounded to 160 nodes. JEV receives compact structured values, ancestor context and bounded action/query criteria. It can select further regions, candidate pages and UTF-16 value ranges; Swift performs filtering, indexed acquisition and pagination. The complete catalogue remains reachable across pages instead of silently dropping controls after the Choice limit. Small UIs stay on the direct path. The native task window uses the natural-language request flow described above.

`overview(scope)`, `find(scope,filter)`, `children(node,cursor)`, `read(node,fields,textRangeUTF16)` and `changes(sinceRevision)` are local store APIs. Scope is the selected process/window, plus that process's menus. Handles are opaque and revision-bound. Cursors bind to their operation/filter/parent/revision. Exact acquired attributes and native parent references stay local. Secure fields and descendants are excluded. Same-name controls retain ancestor context and enabled/selected/checked/focused state. Bridge nodes are compressed structurally rather than summarized with an LLM. All coverage statements refer only to *exposed* AX content; virtualized/unexposed controls still require real scrolling/opening/vision.

Batched metadata reads use `AXUIElementCopyMultipleAttributeValues`; child collection uses `AXUIElementGetAttributeValueCount` and indexed `AXUIElementCopyAttributeValues`. Large text previews and subsequent reads use UTF-16 ranges; outbound bounds and continuation reflect the text actually transmitted. Every omitted value retains a bounded read route, including noneditable status values. A read-only batch can inspect the store without JEV:

```sh
jev-native ax-query --app com.example.app --requests queries.json --out query-results
```

```json
[
  {"kind":"overview"},
  {"kind":"find","filter":{"role":"AXButton","nameContains":"Apply","enabled":true,"ancestorContains":"Right"},"limit":40},
  {"kind":"expand","limit":160},
  {"kind":"children","locator":"w","limit":32},
  {"kind":"read","locator":"w.0","fields":["metadata"]},
  {"kind":"changes"}
]
```

Each request writes `query-N.json`, with `initial.json` and `final-overview.json`. `read` also accepts `value`/`selectedText` and `textRangeUTF16:{"location":0,"length":100}`. These are UTF-16 code units, not grapheme indices. `find` additionally accepts `action`, `selected`, `checked` and `focused`. A locator must already be collected; inspect preceding results rather than guessing a structural path. The `cursor` returned by `find`/`children` belongs to that exact session/query. `delayMS` (maximum 5000) is available for bounded notification diagnostics; it processes notification hints and refreshes before the next request.

AXObserver events invalidate affected loaded subtrees when recognizable. Unknown/root hints force refresh and expire handles. Missing/unsupported notifications remain possible. Ordinary post-action observation refreshes the snapshot, and AX execution validates current role/name/frame, process/window ownership, secure/enabled/focused and observed selected/checked state, the *captured native AXParent*, retained traversal ancestor labels/roles/enabled/security and modal sheets. AXChildren and AXParent are not assumed to be inverse edges. Pointer input continues to compare fresh target images. Button actions do not reread/hash whole documents.

`observation.axMetrics` records instrumented AX read/action/observer API invocations and collection time; these are not a trace of underlying Mach/XPC messages. `decision.requestBytes` is the actual serialized selection request length, and `usage.input_tokens` is returned by TypeSafe. Verification calls add their usage/API time. `JEV_AX_LEGACY=1` is a developer comparison path retaining eager traversal and the old candidate cap; it is not recommended for normal use. Read the [implementation and benchmark evidence](evidence/AX-QUERY.md) for coverage and known uncertainty limits.

Explicit `expectText`/`expectApp` conditions are now authoritative completion predicates. A fresh observation must satisfy **all declared conditions**; pending supplied texts and required text/vision delegates must also be complete. The runner then reports `verified_complete` with `completionSource: explicit_postconditions` without asking JEV to rejudge a literal predicate. `expectText` retains substring matching against observed titles/values/window OCR; `expectApp` compares the selected target bundle. The caller must specify every required final condition: `expectApp` alone proves the selected target identity, not an arbitrary free-form goal. Runs without declared predicates still require JEV's semantic done decision and report `jev_observed_complete`. The legacy benchmark path preserves prior model-gated completion for comparison.

In `ax-query` batches, `cursorFrom:N` uses the continuation returned by preceding `find`/`children` request N (zero-based). `targetFrom:N` and optional `targetIndex` select a node returned by that page. A missing continuation, out-of-range node, mismatched filter/parent or expired revision fails instead of restarting the page. These references allow find→read and paginated inspection without guessing handles.
