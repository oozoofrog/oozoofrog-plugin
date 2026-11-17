# Dashboard screen fixtures

Run from the repository root (Python standard library, Node with built-in WebSocket,
Chrome/Chromium, and ffmpeg must already be available):

```bash
python3 -I -S -B plugins/graph-flow/dev/screens/build_fixtures.py /Volumes/eyedisk/build/graph-flow-screens/r16
node plugins/graph-flow/dev/screens/capture.mjs /Volumes/eyedisk/build/graph-flow-screens/r16
```

The builder replaces only its marked `fixtures/` directory. The capture command
writes the 69 numbered PNGs to `final/`, copies them and makes the requested ffmpeg
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
