# Plan: experiment page for generated reading coaches

Spec: `docs/superpowers/specs/2026-11-24-wild-reading-experiment-page.md`. Status: Proposed. Execution starts only when the user says go.

Paths that start with `skill/` mean `plugins/wild-reading-coach-builder/skills/wild-reading-coach-builder/`. The test file is `scripts/tests/test_wild_reading_coach_builder.py`.

## Order

```text
U1 -> U2 -> U7 -> U3 -> U4 -> U5 (user decision) -> U6
```

U3 can find a defect in the text from U1. In that case, return to U1, then run U3 again.

## Units

| Unit | Depends on | Files | Change | Verification IDs | Live check | Status |
|---|---|---|---|---|---|---|
| U1 | — | `skill/assets/coaching.md`, test file | Add the page procedure, the experiment entry format, and the optional-page sentence. Add the text-contract tests for these IDs. See each test fail before the text exists. | AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6, AC-1.7, AC-1.8, AC-1.9, AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5, AC-2.6, AC-2.7, AC-3.1, AC-3.6 | `python3 -m unittest discover -s scripts/tests -p test_wild_reading_coach_builder.py -v` | done (2026-11-24) |
| U2 | U1 | `skill/SKILL.md`, test file | Add the page loop to the check paragraph. Add the update command for an existing coach. Add the two tests. | AC-3.2, AC-3.10 | Same command as U1 | done (2026-11-24) |
| U3 | U7 | none in the repository | Run walkthrough W1 to W9 in scratch, once in Claude Code and once in Codex. Record each step as pass or fail with the observed output. | AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6, AC-1.7, AC-1.8, AC-1.9, AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5, AC-2.6, AC-2.7, AC-3.7 | The page opened in a browser with the network off | todo |
| U4 | U3 | one existing coach outside the repository | Run the update command on one real coach. One reader completes one experiment from prediction to result. | AC-3.7 | The reader's return visit | todo |
| U5 | U4 | none | The user decides: release, change, or stop. See "Decision after the pilot" in the spec. | — | — | todo |
| U6 | U5 | both `plugin.json` manifests, `CHANGELOG.md`, `README.md`, `README.ko.md`, test file | Set version 0.2.0. Describe the page. Add the test. Do not change the trigger descriptions. | AC-3.3 | `python3 -m unittest discover -s scripts/tests -v` and `git diff --check` | done (2026-11-24) |
| U7 | U2 | `skill/scripts/make_coach.py`, test file | Add the `--update-coaching` option. Write the tests first and see them fail. | AC-3.7, AC-3.8, AC-3.9 | Run the script on a scratch coach under `/Volumes/eyedisk/tmp` and compare file hashes before and after | done (2026-11-24) |

## Notes

- U1 and U2 change instruction text only. Only U7 changes `skill/scripts/make_coach.py`.
- The text-contract tests prove that an instruction is present. U3 is the only proof of coach behavior.
- U4 changes a coach directory that holds a private `PROFILE.md`. Back up that directory to `/Volumes/eyedisk/tmp` first. Do not copy the profile into the repository or into a report.
- U6 does not push or publish. A push is a separate user request.
- 2026-11-24: the user asked to merge and release before U3, U4 and U5. Coach behavior (walkthrough W1 to W9) is not verified in this release.
