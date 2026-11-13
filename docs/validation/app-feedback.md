# App Feedback validation — 2026-11-13

Implemented `app-feedback` 0.1.0 as one shared skill with `assets/AppFeedback/`, a standalone local Swift package. Apps copy the package into their own repository and link its library product. The marketplace root has no `Package.swift`; installed cache paths are not app dependencies. The skill includes update instructions, recipient collection, key setup, stable settings-root presentation, Debug/Release checks, and received-file decryption.

## Executed evidence

Xcode 27.2 (27B48), Apple Swift 6.4.2, macOS on Apple Silicon. Library/tool/test sources were committed at `e6168b21d1aa258b9d57fefd7626049a9b606395`; final complete verification used `2074c7f` (which changes verification scripts and distribution documentation only). Subsequent script edits only allow caller-selected external output folders on other Macs; syntax and rejection of output inside the skill were checked separately. No library, tool, test, or sample-app source changed after the passing builds.

`SKILL` below means `plugins/app-feedback/skills/app-feedback`. The actual output root was `/Volumes/eyedisk/build/oozoofrog-plugin/app-feedback-validation`. SwiftPM scratch, module/configuration/security caches, temporary files, generated Xcode projects and products all used that root. `eyebuild run` wrapped the builds because these were CLI SwiftPM checks and an independent generated app with explicitly located logs, rather than the open workspace in Xcode.

| Executed command/check | Result |
| --- | --- |
| `python3 -B "$SKILL/scripts/verify.py" --output "$BUILD_ROOT/proof-2"` | Passed; library Debug 10 tests, Release 5 tests, all compiler/build warnings **0** |
| Tool's `xcrun swiftc -swift-version 6 -module-cache-path ... feedback_diagnostics.swift -o ...` | Passed, warnings **0** |
| Keychain generate/public-key/duplicate generation | New unique service/account; public export matches; duplicate rejected without replacing the key |
| Library-generated attachment → compiled Mac decrypt tool | Exact synthetic JSON round trip; output permissions `0600` |
| Overwrite, tampered magic/ciphertext and wrong key ID | Each rejected, with no new plaintext output; original output unchanged |
| Library CryptoKit tests | Correct key round trip, wrong private key rejection, header/key/ciphertext tampering and truncated data rejection |
| Release library `nm` check | No `FeedbackDiagnostics`, `FeedbackSealing` or `FeedbackCheck` symbols |
| Temporary Keychain cleanup | Delete exit 0; exact item lookup exit 44 (not found); completed for both verification attempts |
| `python3 -B "$SKILL/scripts/smoke_ios.py" --output "$BUILD_ROOT/smoke-2"` | Independent SwiftUI iOS app, package copied to Vendor, documented code extracted verbatim; Debug and Release generic iOS Simulator builds passed |
| iOS app warnings | Compiler/library **0**; Apple metadata tool **1 per configuration**, detailed below |
| `TMPDIR="$BUILD_ROOT/test-tmp" python3 -I -S -B -m unittest discover -s scripts/tests -v` | **50 passed**; includes marketplace inventory, both manifests, metadata, local links, and routing fixtures under `tests/` |
| Same unittest command with `-s plugins/guided-execution/skills/guided-execution/tests` | **90 passed** |
| `quick_validate.py "$SKILL"` with an existing Python installation containing PyYAML | `Skill is valid!` |
| Python `py_compile` for both new verification helpers | Passed, bytecode cache outside the repository |
| Both helpers invoked with an output directory inside the skill | Exit 2 before writes, as intended |
| `git diff --check` | Passed |

The iOS builds run `xcodebuild -project <temporary project> -scheme FeedbackExample -configuration Debug/Release -destination 'generic/platform=iOS Simulator' -derivedDataPath <external path> -clonedSourcePackagesDirPath <external path> build`. The package uses Swift 6 and declares iOS 17/macOS 14 deployment minimums; minimum-OS runtime execution was not performed.

Apple's `appintentsmetadataprocessor` emits:

> warning: Metadata extraction skipped, no AppIntents.framework dependency found

The sample app has no App Intents. The verifier reports and retains this exact Apple-tool diagnostic separately; every compiler warning and every other tool warning fails. No warning-suppression flags or unrelated framework dependency were added.

## Corrections found during verification

- Xcode 27's SwiftPM build system produced `swiftpm/out/Products/Release/AppFeedback.o`, not the older per-file object layout. The first symbol-path check failed after successful tests and tool round trip; it now accepts both actual output layouts. The complete helper then passed.
- The first smoke helper treated the Apple metadata message as a compiler failure despite exit 0. The final helper distinguishes that exact tool message and reports its count.
- The existing guided-execution suite initially failed 7 checks because macOS's default temporary directory traverses `/var` → `/private/var`, violating its symlink/path assertions. Re-running with `TMPDIR` under the explicit eyedisk build root passed all 90 without changing that plugin.
- Default Homebrew Python lacked PyYAML. An already-installed Python with PyYAML ran the skill validator; no dependency was installed.

## Scope and limits

The generic package injects recipient, app metadata, mail content, UI copy, public key, a bounded JSON diagnostics provider and optional checklist. It preserves Debug-only encryption/attachment construction, opt-out, failure reporting, mailto plus address-copy/share fallback, and presentation above changing Form rows. mailto bodies do not falsely claim an attachment. Private keys remain in the selected Mac Keychain item; no private-key export or repository-key fallback is shipped.

App-specific logs, storage, domain events, device transport, issue lists, fixed recipients, keys and identifiers were not copied. This package does not collect observations automatically. A host provider must redact and bound its own data and compile collection out of Release. Checklist state is in memory. Temporary shared files contain ciphertext only.

This establishes macOS model/crypto tests and iOS Simulator compilation. It does **not** establish actual Mail composer lifecycle, physical-device attachment or email delivery, share-sheet runtime, screenshots/visual appearance, dedicated accessibility checks, UIKit hosting runtime, old-OS runtime, other-platform UI, marketplace installation or fresh-session skill exposure. The iOS-only native result mapping test is present but was not executed by the macOS test run. No UI geometry assertions were added.

Both hosts' manifests and catalogs are registered on the PR branch. Until merge, this is not published availability on the remote `main` catalog. No merge, tag, marketplace reinstall or device installation was performed.

All task build folders and temporary Keychain items were removed after verification. Only this small verification record remains in the repository; no keys, generated app, binary, plaintext report, DerivedData or build cache is retained.
