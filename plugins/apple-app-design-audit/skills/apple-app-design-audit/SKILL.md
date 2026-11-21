---
name: apple-app-design-audit
description: Use when auditing or improving the design of a native SwiftUI or AppKit app for macOS, iOS, or iPadOS against Apple's Human Interface Guidelines and Liquid Glass, including toolbars, sidebars, search, empty and error states, Settings, Dark Mode, contrast, text size, and destructive actions. Reads current Apple guidance through Xcode MCP DocumentationSearch and the files bundled in Xcode. 맥앱·iOS 앱 디자인 점검, HIG·Liquid Glass 기준 검토, 디자인 개선 요청에 사용한다. Not for web UI, cross-platform frameworks, App Store screenshots, or copy-only edits.
---

# Apple App Design Audit

Audit a native Apple app the way a careful reviewer would: run the real app, look at every state a person can reach, compare what you see with Apple's current guidance, and propose fixes that use system components before custom ones. Then fix and verify in the same running app.

Project instructions and the user's instructions take precedence. When they say who implements changes (for example, a delegated agent), follow them.

## Why this order

Most design defects only show up in a state the developer rarely sees: no search results, a failed import, a narrow window, Dark Mode after a cold launch. Source reading alone misses them, and screenshots alone miss their cause. Run the app first, then read the code behind each defect.

Apple's guidance changes with each OS release. Read it from the installed Xcode rather than from memory or a saved copy, and cite the article you relied on.

## Workflow

1. **Gather the guidance.** Read [references/sources.md](references/sources.md). Use Xcode MCP `DocumentationSearch` for HIG articles and API pages. Read the Liquid Glass and toolbar guides that ship inside Xcode. Do not copy these documents into the project; cite their URIs or paths.
2. **Know the targets.** Read the deployment targets (for example `MACOSX_DEPLOYMENT_TARGET`) and the SDK version. Every new API you propose must be available on the lowest target, or gated with `#available`. Check availability in the SDK's `.swiftinterface`, not from memory.
3. **Build and run the real app.** Follow the project's build instructions. Capture the state matrix in [references/checklist.md](references/checklist.md): appearances, accessibility display settings, window sizes, and content states. Save captures outside the repository, in the location the user's rules require.
4. **Inspect each defect at its source.** For each visible problem, find the code that causes it. Separate what you observed (capture, accessibility tree, runtime log) from what you inferred. State an inferred cause as an inference until you have reproduced it.
5. **Report findings.** Use the report format below. Rank by user harm: data loss and unreachable features first, then missing states, then layout and visual polish.
6. **Ask only about what the user can see.** Before asking the user to choose between designs, run the build that contains the choice or put the captures in the message and point to the exact spot. If you cannot show it, pick the option that follows the HIG and report the choice.
7. **Fix with system components first.** Prefer `NavigationSplitView`, semantic `ToolbarItem` placements, `.searchable`, `ContentUnavailableView`, the `Settings` scene, menu commands, and system materials. Remove custom backgrounds from bars, sidebars, and sheets before adding anything. See [references/pitfalls.md](references/pitfalls.md) for fixes that needed more than the obvious change.
8. **Verify in the running app.** Recapture the same states after the fix. Check both appearances and the narrowest supported window. Build every platform target that shares the changed views. Report what you could not verify (another OS version, a physical device, live network or iCloud behavior, real keyboard input).

## Report format

Start with the count of findings and which ones to fix first. Then give one row per finding:

| # | Problem (what a person sees, and when) | Proposal (system component or behavior) | Size |
|---|---|---|---|

- Attach the capture path for each visual finding, and the source location for each cause.
- Cite the HIG article or Apple guide behind each proposal.
- List what passed, so the user knows it was checked: for example, no glass in the content layer, contrast ratios that meet 4.5:1, no soft-deprecated APIs.
- List the states you could not reach and why.

## Rules that prevent the most rework

- **Destructive commands act only on what is visible and focused.** A hidden selection (filtered out by search, or behind a sheet) must not be deletable by a shortcut. Name the command after its object ("Delete Document"), and make it recoverable (Trash plus Undo) on macOS.
- **Every toolbar item has a menu command.** People can hide or customize the toolbar, and narrow windows push items into overflow.
- **Settings live in the `Settings` scene** (App menu, `⌘,`), never only behind a Debug-only button.
- **Every list has its empty, no-results, failed, and in-progress states.** A selected failed item shows its own detail and recovery actions, not "Select an item".
- **No custom backgrounds on navigation, toolbars, sidebars, or sheets; no glass in the content layer.** Use the scroll edge effect instead of a solid strip under controls.
- **Mac apps have no Dynamic Type.** Offer View menu text size commands (`⌘+`, `⌘−`, `⌘0`) and persist the setting.
- **Measure contrast; do not estimate it.** Compute the ratio for both appearances and record it in the report.
