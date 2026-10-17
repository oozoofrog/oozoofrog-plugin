#!/usr/bin/env python3
"""Build/launch a fresh native identity using the unchanged production core.

No TCC reset, grant, permission mocks, personal profile edits, or clipboard reads.
The evidence directory keeps the test build; the controller state is private.
"""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import time
import uuid

skill = Path(__file__).resolve().parent.parent
run_id = str(uuid.uuid4()).lower()
output = skill / "evidence" / "permissions-none" / run_id
output.mkdir(parents=True, mode=0o700)
state_container = Path(tempfile.mkdtemp(prefix="macpilot-permission-state-"))
state = state_container / "state"  # Store creates and marks this owned directory.
live_output = state_container / "evidence"
live_output.mkdir(mode=0o700)
bundle_id = "local.macpilot.permissionprobe." + run_id.replace("-", "")
app = state_container / "MacPilot Permission Probe.app"
contents = app / "Contents"
(contents / "MacOS").mkdir(parents=True)
(contents / "Resources").mkdir()
probe = skill / "scripts" / "permission_unprivileged_probe.swift"
core = sorted((skill / "tool" / "Sources" / "MacPilotCore").glob("*.swift"))
manifest = {"runID": run_id, "bundleID": bundle_id, "applicationPath": str(app),
            "stateDirectory": str(state), "evidenceDirectory": str(output),
            "liveEvidenceDirectory": str(live_output),
            "coreSHA256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in core},
            "probeSHA256": hashlib.sha256(probe.read_bytes()).hexdigest(),
            "permissionResultsInjected": False, "tccResetPerformed": False}
(output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"status": "building", "runID": run_id, "evidenceDirectory": str(output)}), flush=True)
with (output / "compile.log").open("w") as log:
    subprocess.run(["/usr/bin/xcrun", "swiftc", "-swift-version", "5", "-parse-as-library",
                    "-module-name", "MacPilotPermissionProbe", *map(str, core), str(probe),
                    "-o", str(contents / "MacOS" / "macpilot")], check=True, stdout=log, stderr=log)
info = {"CFBundleIdentifier": bundle_id, "CFBundleExecutable": "macpilot", "CFBundleName": "MacPilot Permission Probe",
        "CFBundleDisplayName": "MacPilot Permission Probe", "CFBundlePackageType": "APPL", "LSUIElement": True,
        "CFBundleShortVersionString": "1.0", "CFBundleVersion": "1", "LSMinimumSystemVersion": "14.0",
        "CFBundleIconFile": "MacPilot.icns", "NSHighResolutionCapable": True,
        "NSAppleEventsUsageDescription": "Test the MacPilot native permission request without granting access.",
        "NSScreenCaptureUsageDescription": "Test the MacPilot native screen capture permission request.",
        "NSAudioCaptureUsageDescription": "Test permission behavior without recording audio."}
with (contents / "Info.plist").open("wb") as f:
    plistlib.dump(info, f)
icon = skill / "bin" / "MacPilot.app" / "Contents" / "Resources" / "MacPilot.icns"
(contents / "Resources" / "MacPilot.icns").write_bytes(icon.read_bytes())
subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", "--identifier", bundle_id, str(app)], check=True)
subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)], check=True)
with (output / "launch.log").open("w") as log:
    subprocess.run(["/usr/bin/xcrun", "swift", str(skill / "scripts" / "permission_probe_launcher.swift"),
                    str(output / "manifest.json")], check=True, stdout=log, stderr=log)
for _ in range(100):
    if (live_output / "baseline.json").exists():
        break
    time.sleep(0.1)
else:
    raise RuntimeError("Native probe did not produce baseline evidence")
baseline = json.loads((live_output / "baseline.json").read_text())
shutil.copy2(live_output / "baseline.json", output / "baseline.json")
print(json.dumps({"status": "baseline", "evidenceDirectory": str(output), **baseline}), flush=True)
assert baseline["bundleID"] == bundle_id
assert not any(baseline["permissions"].values()), "OS grants exist; not a no-permission test"
(skill / "evidence" / "permissions-none" / "latest.json").write_text(json.dumps({"evidenceDirectory": str(output)}, indent=2) + "\n")

def control(operation, kind=None):
    command = ["/usr/bin/python3", str(skill / "scripts" / "permission_probe_control.py"), str(output), operation]
    if kind is not None:
        command += ["--kind", kind]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    response = json.loads(result.stdout)
    snapshot = response["snapshot"]
    assert not any(snapshot["permissions"].values()), "Probe acquired a permission during verification"
    return snapshot

initial = control("inspect")
assert initial["kind"] == "accessibility" and initial["draggable"]
assert initial["autoAddExists"] and not initial["autoAddEnabled"]
blocked = control("auto_add")
assert "Accessibility / Post Event access is required" in blocked["tooltip"]
cases = []
drop_kinds = {"accessibility", "screenCapture", "postEvent", "inputMonitoring", "fullDiskAccess"}
for kind in ["accessibility", "screenCapture", "postEvent", "inputMonitoring", "fullDiskAccess", "files", "clipboard", "automation"]:
    snapshot = control("select", kind)
    assert snapshot["kind"] == kind
    assert snapshot["draggable"] == (kind in drop_kinds)
    assert not snapshot["autoAddEnabled"]
    cases.append(snapshot)
sequence = [control("select", "all"), control("next"), control("next"), control("previous")]
assert [x["kind"] for x in sequence] == ["accessibility", "screenCapture", "automation", "screenCapture"]
summary = {"status": "passed", "baseline": baseline, "initial": initial, "autoAddBlocked": blocked,
           "cases": cases, "sequence": sequence, "nativeManualDrag": "separate driver required",
           "nativeConsentPrompt": "not requested by the automatic matrix", "probeLeftRunning": True}
(output / "automatic-report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
for evidence in live_output.glob('*.json'):
    shutil.copy2(evidence, output / evidence.name)
print(json.dumps({"status": "matrix_passed", "evidenceDirectory": str(output), "caseCount": len(cases)}), flush=True)
