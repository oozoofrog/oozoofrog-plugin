# Audit checklist

## State matrix

Capture each screen in these conditions. Name captures by number, screen, and condition (for example `07-search-no-results-light.jpg`) so the report can cite them.

- **Appearance:** Light, Dark. Capture Dark Mode after a cold launch as well as after a live switch; some defects appear in only one.
- **Accessibility display settings:** Reduce Transparency; Increase Contrast together with Reduce Transparency.
- **Window size (macOS):** the minimum size, about 900 pt wide, and a wide window. Toolbar overflow usually starts near the middle size.
- **Size class (iOS, iPadOS):** compact and regular widths; the largest accessibility text size.
- **Content states:** empty library; a populated list; search with results; search with no results; an item in progress; a failed item, selected; a very long title; each sheet and the Settings window.
- **Scroll position:** top of each scrolling view and scrolled under the toolbar, for the scroll edge effect.

Also record the accessibility tree for the main window. It shows duplicate labels (for example many links named "Open Original") and controls without names.

## What to check

Each item lists the failure seen in a real audit, so you know what it looks like.

1. **Destructive actions.** Delete must act only on a visible, focused selection. Failure: with zero search results, the previous document stayed open and `⌫` deleted it; the Edit menu had two items named "Delete"; the folder was removed permanently.
2. **Settings reachability.** Failure: the only way to change the storage location was a gear button that existed only in Debug builds.
3. **Toolbar at narrow widths.** Failure: at 900 pt the primary command (Paste Address) moved into overflow; there were two search entry points; the sidebar toggle sat behind other buttons.
4. **Search results and empty search.** Failure: no-results left a blank sidebar; body matches ranked above title matches; snippets showed raw Markdown symbols.
5. **Text size on macOS.** Failure: the reader had no way to change text size. macOS has no Dynamic Type, so the app must provide View menu commands.
6. **Dark Mode surfaces.** Failure: a 17 pt light strip at the trailing edge of a web-based reader in Dark Mode. See pitfalls.
7. **Failed and in-progress items.** Failure: selecting a failed import showed "Select a Document" instead of the address, the error, and Retry.
8. **Row density.** Failure: sidebar rows about 81 pt tall, with thumbnails, full timestamps, and a "Complete" badge that pushed titles into truncation.
9. **Sheets and backgrounds.** Failure: painted backgrounds hid the system material in sheets and Settings; a duplicate-item sheet had no clear default button. Name buttons by result ("Open Existing", "Save as New Edition").
10. **Link and secondary text contrast.** Failure: a link arrow at 3.28:1, below 4.5:1. Compute ratios for both appearances.
11. **Titles and dates.** Failure: the toolbar title repeated the document heading; dates showed seconds and the time zone. Use the user's locale format.
12. **Scroll edge.** Failure: native lists blurred content under the toolbar, but the web-based reader clipped its first line.

## What passing looks like

Record these as checked, with the evidence:

- No `glassEffect` or custom glass in the content layer; bars and sidebars use system materials.
- Text contrast ratios at or above 4.5:1 (3:1 for large text) in both appearances.
- No soft-deprecated SwiftUI APIs (compare with Xcode's `swiftui-specialist-ref-soft-deprecated-apis`).
- Every toolbar command also exists in the menu bar.
- Readable line length in a wide window.
