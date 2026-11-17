# Dashboard screen fixtures

Run from the repository root (Python standard library, Node with built-in WebSocket,
Chrome/Chromium, and ffmpeg must already be available):

```bash
python3 -I -S -B plugins/graph-flow/dev/screens/build_fixtures.py /Volumes/eyedisk/build/graph-flow-screens/r20
node plugins/graph-flow/dev/screens/capture.mjs /Volumes/eyedisk/build/graph-flow-screens/r20
```

The builder replaces only its marked `fixtures/` directory. The capture command
writes the 97 numbered PNGs to `final/`, copies them and makes the requested ffmpeg
variants in `verify/`, and records DOM observations, hashes, and process cleanup
outside those directories. An optional third argument, e.g. `5,16`, recaptures only
those numbers. Rebuild fixtures before a fresh full capture. No installs or real
user state are used; every scenario has its own GF_HOME and scratch Git project.
Only the processes started by this command are stopped. No `gf open` is used.

`screens.json` defines every deep link, viewport, interaction and review group.
`SCENARIOS` in `build_fixtures.py` describes each fixture: demo/real/many/large/30
cover working graphs; plan/sent-back/changed-live/replaced cover consent;
files/nothing/hold/outcomes/free/revised/answered/review-awaited cover decisions;
constraints/check-options/own-files cover checks; tampered/unverified/key-*/moved
cover integrity and recovery; old* restores the suite's genuine 0.2.1 record;
wording covers a wording-only repost. Normal history comes from the real CLI;
human answers use `tests/human_support.py`. Only historical and tampering fixtures
reuse the suite's raw-record operations. Names, content and Git dates are fixed;
CLI event timestamps, check duration, nonces and signatures are intentionally real.

The cheap repository test validates the manifest without starting any processes.
Developer tools remain outside `skills/`; plugin manifests keep loading only the
existing skill/runtime. Captures report defects without editing product assets.

Round 17 distinguishes the fitted large plan at 1280px from the default 1440px overview; the large run advances three pieces and starts the next branch. The unverified-plan scene stays on the graph, while the problem inbox scene opens My turn. Legacy fixture prose is translated only in the isolated capture copy.

Round 18 captures enlarged lower rows with vertical scrolling (11), the unverified answer record (27) separately from its graph banner (36), and the new consent after on-page key recovery (56). Scene 66 uses the permission button’s actual rejected outcome. Captures assert panel/graph relations, change titles, content bounds and the named scene states.

Round 19 adds selected work/review/decision/final-check cards at both sizes (70–77) and maximum-length Korean text in detail/overview desktop/phone views (78–81). The first explanation stays pinned below the title. Scene 56 selects the final check after on-page recovery, unlike the unselected terminal recovery in 35. Capture validates visible explanations, actual text bounds, relations and owned-process cleanup. Verification includes all requested images plus the prior 34/38 variants.


Round 20 adds the missing phone decisions and trajectory, lane-3 permission, decision review, failed host check, changed-evidence re-ask and plan re-approval at both sizes (82–97). The trajectory uses three real submissions, a failed run check, a failed node check, and failed then passing reviews. Marked `decision_screen` scenes assert Q1–Q5 order, distinct consequences, viewport bounds, unchanged polling and the exhausted-attempt cost; every decision also receives gray/glance copies.
