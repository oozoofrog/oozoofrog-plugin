# Pitfalls and their fixes

Each entry is a defect whose first obvious fix was wrong or incomplete. Confirm the cause in your own app before applying a fix; these are patterns, not guarantees.

## WKWebView reader on macOS

**A light strip at the trailing edge in Dark Mode.** The page CSS had switched to its dark palette, but the app set `underPageBackgroundColor` from an AppKit named color. On macOS, that color filled the legacy (always-shown) scroller track with the light value. Fix: on macOS, do not set `underPageBackgroundColor` from AppKit. Let WebKit derive it from the page: give `:root` the page background (`:root { background: var(--paper); }`) and declare `color-scheme` so the CSS follows the system appearance. Verify a live appearance switch, a cold Dark Mode launch, and both scroll bar settings (System Settings → Appearance → Show scroll bars: Always / When scrolling).

**The first line is clipped under the toolbar, with no scroll edge effect.** SwiftUI's `scrollEdgeEffectStyle` applies to SwiftUI scroll views, not to a web view. Fix: let the web view extend under the toolbar, and set `obscuredContentInsets` (macOS 26) to the height covered by the title bar so the page starts below it:

```swift
final class ReaderWebKitView: WKWebView {
    override func layout() {
        super.layout()
        guard let window else { return }
        let visible = convert(window.contentLayoutRect, from: nil)
        let top = max(0, isFlipped ? visible.minY - bounds.minY : bounds.maxY - visible.maxY)
        if obscuredContentInsets.top != top {
            obscuredContentInsets = NSEdgeInsets(top: top, left: 0, bottom: 0, right: 0)
        }
    }
}
```

If the page has a sticky header, fade it with a gradient to the page color instead of a solid strip.

**Links cannot be reached with Tab.** Set `configuration.preferences.tabFocusesLinks = true` on macOS and give links a visible `:focus-visible` outline.

## Toolbars

**The primary command falls into overflow at medium widths.** Fix the order and placements first: keep the sidebar toggle leading, use semantic `ToolbarItem` placements, keep one search item (from `.searchable`), and group the rest. Then raise the priority of the one command that must stay: `.visibilityPriority(.high)`. That modifier is new; in the macOS 27 SDK it is `@available(macOS 26.1, iOS 27.0, *)`. Check the SDK (see sources.md) and gate it for lower deployment targets.

**The toolbar repeats the document title.** On macOS, hide the toolbar title with `.windowToolbarStyle(.unified(showsTitle: false))` and keep `.navigationTitle(...)`. The title then still names the window in the Window menu and Mission Control. Use a list title ("Documents") when nothing is selected.

## Destructive actions and the sandbox

**Delete removes a document hidden by search.** Enable the command only when the focused list shows the selected row. Remove or hide the system text "Delete" item from the Edit menu when it duplicates the app's command.

**Recovery from the Trash fails for iCloud documents.** In a sandboxed Mac app, `FileManager.trashItem` on an item in the iCloud container moves it to iCloud Drive's Trash, and the sandbox then denies moving it back. Fix: first move the folder into the app's local container, then trash it from there. Register Undo with the resulting Trash URL and restore to the original library. If the library location changed or the destination exists, leave the item in the Trash. If trashing fails, ask before deleting permanently. Record this as an architecture decision; the next maintainer will otherwise "simplify" it back.

## Search

**No-results state.** Use `ContentUnavailableView.search(text:)` or a `ContentUnavailableView` with a Clear Search button. Do not keep the previous document open in the detail pane without saying that it is outside the results.

**Ranking and snippets.** Rank title matches above body matches. Strip Markdown before building snippets, and emphasize the query in the snippet.

## Mac text size

Add `CommandGroup(after: .toolbar)` with Increase (`⌘+`), Decrease (`⌘−`), and Actual Size (`⌘0`). Store the value (for example 75–200 %) in `@AppStorage`. For a web reader, apply it with a script call instead of reloading the page, so the reading position stays.

## Tooling

**UI automation could not send shortcuts.** Some automation tools cannot deliver key equivalents to SwiftUI menu commands. Verify through the menu item, and report the shortcut itself as unverified rather than passed.

**Products in the repository.** Xcode's per-user Locations setting can put build products in a `Build/` folder inside the checkout. Check the effective `BUILT_PRODUCTS_DIR` before a long run, and launch the app from where it was built.
