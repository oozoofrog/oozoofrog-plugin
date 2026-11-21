# Apple App Design Audit 0.1.0 validation

This records where the skill's content came from and which checks ran. No behavioral evaluation (with-skill and baseline runs on test prompts) was run for 0.1.0.

## Source of the content

The workflow, checklist, and pitfalls come from one design audit of a sandboxed macOS SwiftUI document app on macOS 27 with Xcode 27.2 (2026-11-20 to 2026-11-21). The audit captured 21 states, found 12 defects, and fixed all of them. Each fix was built for macOS and iOS and checked in the running Mac app. The checklist items describe those defects without project names or data.

Facts in the references were checked against the installed tools on 2026-11-21:

- Xcode MCP `DocumentationSearch` returned HIG articles (Materials: Liquid Glass, Toolbars: macOS, Sidebars, Settings: macOS, the Window menu) with full text.
- The `AdditionalDocumentation/` folder and the `swiftui-specialist` and `swiftui-whats-new-27` files exist in Xcode 27.2. The `.packaged` files are UTF-8 Markdown.
- The macOS 27.2 SDK declares `visibilityPriority` as `@available(iOS 27.0, macOS 26.1, ...)`, `WKWebView.obscuredContentInsets` as `API_AVAILABLE(macos(26.0))`, and `ContentUnavailableView.search(text:)`. The availability command in `references/sources.md` printed the expected lines.

## Structural checks

- skill-creator `quick_validate`: passed.
- `python3 -m unittest discover -s scripts/tests`: 64 tests passed, including the marketplace inventory, manifest, metadata, and local link checks.
- `git diff --check`: no whitespace errors.

## Not verified

- Behavior with and without the skill on new prompts.
- Automatic skill selection from the description.
- Use on iOS or iPadOS apps, on AppKit-only apps, or with an Xcode release other than 27.2. File names in Xcode can change between releases; the skill tells the agent to list the folders first.
