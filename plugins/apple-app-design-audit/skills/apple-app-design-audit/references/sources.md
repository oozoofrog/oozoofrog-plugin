# Apple guidance sources

Read guidance from the installed Xcode. It matches the SDK the project builds with, and it updates when Xcode updates. A saved copy goes stale and adds files nobody maintains.

## 1. Xcode MCP `DocumentationSearch`

The Xcode MCP server (`xcrun mcpbridge`) exposes `DocumentationSearch`. It returns Human Interface Guidelines articles (URIs under `/design/Human-Interface-Guidelines/`) and API reference pages (`/documentation/...`) with their full text. Xcode must be running.

The search is semantic, so plain topic words work. Starting queries for a macOS document app (refine them when the results drift):

| Topic | Query |
|---|---|
| Liquid Glass and materials | `Liquid Glass materials content layer` |
| Toolbars | `toolbars macOS menu bar command` |
| Sidebars and split views | `sidebars macOS split view` |
| Window menu and titles | `the menu bar Window menu` |
| Settings | `Settings macOS App menu Command-Comma` |
| Search | `search fields scope no results` |
| Empty states | `ContentUnavailableView search` |
| Layout and scroll edge | `layout visual hierarchy scroll edge effect` |
| Color and contrast | `color contrast accessibility Dark Mode` |
| Text size | `typography Dynamic Type macOS` |
| Destructive actions | `alerts destructive action undo` |

Narrow with `frameworks: ["SwiftUI"]` for API pages. Cite the returned `uri` in the report.

## 2. Guides bundled in Xcode

These Markdown files ship with Xcode and are written by Apple:

```
/Applications/Xcode.app/Contents/PlugIns/IDEIntelligenceChat.framework/Versions/A/Resources/AdditionalDocumentation/
```

Read the ones that match the platform and frameworks:

- `SwiftUI-Implementing-Liquid-Glass-Design.md`, `AppKit-Implementing-Liquid-Glass-Design.md`, `UIKit-Implementing-Liquid-Glass-Design.md`
- `SwiftUI-New-Toolbar-Features.md`
- `SwiftUI-WebKit-Integration.md` (for apps that show web content)

List the folder first; file names change between Xcode releases.

## 3. Xcode's SwiftUI guidance prompts

Xcode's own coding assistant uses SwiftUI guidance files in the parent `Resources/` folder. They are plain UTF-8 Markdown despite the `.packaged` extension. They are not Claude Code or Codex skills, and no MCP tool loads them. Read them directly:

```sh
R=/Applications/Xcode.app/Contents/PlugIns/IDEIntelligenceChat.framework/Versions/A/Resources
ls "$R" | grep -E '^swiftui-'
```

- `swiftui-specialist.idechatprompttemplate` and `swiftui-specialist-ref-*.md.packaged`: best practices. `-ref-soft-deprecated-apis` lists APIs to replace.
- `swiftui-whats-new-<version>.idechatprompttemplate` and its refs: new APIs in the current SDK, including toolbar changes.

## 4. API availability

Read availability from the SDK, not from memory or a guide's prose. For example, to check a SwiftUI modifier on macOS:

```sh
SDK=$(xcrun --sdk macosx --show-sdk-path)
grep -n -B2 'func visibilityPriority' \
  "$SDK/System/Library/Frameworks/SwiftUI.framework/Versions/A/Modules/SwiftUI.swiftmodule/arm64e-apple-macos.swiftinterface" \
  | grep '@available'
```

Use `iphoneos` and the iOS interface for iOS. Compare the result with the project's deployment target and gate with `#available` when needed. Use the same version in every gate for the same API.
