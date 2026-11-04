#!/usr/bin/env python3
"""Evidence-only continuous-pixel preview/retarget reproduction on owned windows.

No production changes or input events. The runner compiles a private two-window
5 Hz fixture and a read-only ScreenCaptureKit/pixel probe. Run serially.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import traceback

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--binary', type=Path, required=True)
p.add_argument('--evidence', type=Path, required=True)
p.add_argument('--samples', type=int, default=12)
a = p.parse_args()
binary = str(a.binary.resolve()); out = a.evidence.resolve(); out.mkdir(parents=True, exist_ok=False)
root = Path(tempfile.mkdtemp(prefix='macpilot-preview-live-'))
env = dict(os.environ, MACPILOT_STATE_DIR=str(root/'state'))
fixture = None; hosts = []; checks = []; samples = []; failures = []; cleanup_errors = []
completed = False; sequence = 0

FIXTURE = r'''
import AppKit
final class Pattern: NSView {
 var sequence = 0; var target = 1
 override func draw(_ dirty: NSRect) {
  let color = target == 1 ? NSColor(srgbRed: 0.82, green: 0.12, blue: 0.18, alpha: 1) : NSColor(srgbRed: 0.12, green: 0.32, blue: 0.84, alpha: 1)
  color.setFill(); bounds.fill()
  let code = (target << 10) | (sequence % 1024)
  for bit in 0..<12 {
   NSColor(calibratedWhite: ((code >> bit) & 1) == 1 ? 0.96 : 0.04, alpha: 1).setFill()
   NSRect(x: bounds.width*(0.08 + Double(bit)*0.07), y: bounds.height*0.35, width: bounds.width*0.07, height: bounds.height*0.30).fill()
  }
 }
}
final class Fixture: NSObject, NSApplicationDelegate {
 let directory: URL; var windows: [NSWindow] = []; var views: [Pattern] = []; var timer: Timer?; var history: [[String: Any]] = []; var number = 0
 init(_ directory: URL) { self.directory = directory }
 func applicationDidFinishLaunching(_ notification: Notification) {
  for index in 0..<2 {
   let window = NSWindow(contentRect: NSRect(x: 100 + index*160, y: 170 + index*80, width: 640, height: 420), styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
   window.title = "Owned Preview Target \(index+1)"; window.isReleasedWhenClosed = false
   let view = Pattern(frame: NSRect(x: 0, y: 0, width: 640, height: 420)); view.autoresizingMask = [.width, .height]; view.target = index+1
   window.contentView = view; window.orderFrontRegardless(); windows.append(window); views.append(view)
  }
  timer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in self?.tick() }; tick()
 }
 func tick() {
  number += 1
  for view in views { view.sequence = number; view.needsDisplay = true; view.displayIfNeeded() }
  history.append(["sequence": number%1024, "monotonic": ProcessInfo.processInfo.systemUptime, "unixTime": Date().timeIntervalSince1970])
  if history.count > 256 { history.removeFirst(history.count-256) }
  let state: [String: Any] = ["pid": getpid(), "sequence": number%1024, "windows": windows.enumerated().map { ["target": $0.offset+1, "windowID": $0.element.windowNumber] }, "history": history]
  if let data = try? JSONSerialization.data(withJSONObject: state) { try? data.write(to: directory.appendingPathComponent("fixture.json"), options: .atomic) }
 }
}
let directory = URL(fileURLWithPath: CommandLine.arguments[1]); let app = NSApplication.shared
let fixture = Fixture(directory); app.setActivationPolicy(.accessory); app.delegate = fixture; app.run()
'''

PROBE = r'''
import AppKit
import ScreenCaptureKit
import ImageIO
import Darwin
func identity(_ pid: Int32) -> String? {
 var info = proc_bsdinfo(); let size = Int32(MemoryLayout<proc_bsdinfo>.size)
 guard proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &info, size) == size, Int32(info.pbi_pid) == pid else { return nil }
 return "\(info.pbi_start_tvsec).\(info.pbi_start_tvusec)"
}
func decode(_ image: CGImage) throws -> [String: Any] {
 let width = image.width, height = image.height
 var pixels = [UInt8](repeating: 0, count: width*height*4)
 guard let context = CGContext(data: &pixels, width: width, height: height, bitsPerComponent: 8, bytesPerRow: width*4,
  space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { throw NSError(domain: "pixels", code: 1) }
 context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
 var code = 0; var bands: [[Int]] = []
 for bit in 0..<12 {
  let x = min(width-1, Int(Double(width)*(0.115 + Double(bit)*0.07))); let y = height/2; let offset = (y*width+x)*4
  let color = [Int(pixels[offset]), Int(pixels[offset+1]), Int(pixels[offset+2])]; bands.append(color)
  if color.reduce(0,+) > 3*128 { code |= 1 << bit }
 }
 return ["target": code >> 10, "sequence": code & 1023, "bands": bands, "width": width, "height": height]
}
@main struct Probe {
 @MainActor static func main() async {
  do {
   let args = CommandLine.arguments
   if args[1] == "identity" {
    let pid = Int32(args[2])!
    let rows = CGWindowListCopyWindowInfo([.optionAll, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
    let owned = rows.filter { ($0[kCGWindowOwnerPID as String] as? Int32) == pid }
    let windowIDs = owned.compactMap { ($0[kCGWindowNumber as String] as? NSNumber)?.intValue }
    let windows: [[String: Any]] = owned.map { ["windowID": $0[kCGWindowNumber as String] ?? 0, "title": $0[kCGWindowName as String] ?? "", "frame": $0[kCGWindowBounds as String] ?? [:]] }
    print(String(data: try JSONSerialization.data(withJSONObject: ["pid": pid, "processStartID": identity(pid) as Any? ?? NSNull(), "windowIDs": windowIDs, "windows": windows]), encoding: .utf8)!); return
   }
   var image: CGImage
   if args[1] == "capture" {
    let application = NSApplication.shared
    application.setActivationPolicy(.prohibited)
    guard CGPreflightScreenCaptureAccess() else { throw NSError(domain: "screen_capture_denied", code: 8) }
    let pid = Int32(args[2])!, start = args[3], windowID = UInt32(args[4])!
    guard identity(pid) == start else { throw NSError(domain: "identity", code: 2) }
    let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: false)
    guard let window = content.windows.first(where: { $0.windowID == windowID && $0.owningApplication?.processID == pid }) else { throw NSError(domain: "window", code: 3) }
    let filter = SCContentFilter(desktopIndependentWindow: window), config = SCStreamConfiguration()
    config.width = max(1, Int(filter.contentRect.width*2)); config.height = max(1, Int(filter.contentRect.height*2)); config.ignoreShadowsSingleWindow = true; config.showsCursor = false
    image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
    guard identity(pid) == start else { throw NSError(domain: "identity", code: 4) }
    let url = URL(fileURLWithPath: args[5]); guard let destination = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else { throw NSError(domain: "png", code: 5) }
    CGImageDestinationAddImage(destination, image, nil); guard CGImageDestinationFinalize(destination) else { throw NSError(domain: "png", code: 6) }
   } else {
    guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: args[2]) as CFURL, nil), let read = CGImageSourceCreateImageAtIndex(source, 0, nil) else { throw NSError(domain: "png", code: 7) }
    image = read
   }
   var result = try decode(image); result["unixTime"] = Date().timeIntervalSince1970; result["monotonic"] = ProcessInfo.processInfo.systemUptime
   print(String(data: try JSONSerialization.data(withJSONObject: result), encoding: .utf8)!)
  } catch { fputs("\(error)\n", stderr); exit(2) }
 }
}
'''


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2))


def report():
    dump(out/'report.json', dict(schema='macpilot-preview-live/1', suiteStatus='passed' if completed and not failures and not cleanup_errors and all(c['passed'] for c in checks) else 'failed',
        completed=completed and not cleanup_errors, bodyFailures=failures, cleanupFailures=cleanup_errors, checks=checks, samples=samples,
        binary=binary, binarySHA256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(), isolatedState=str(root),
        limits='Synthetic 5 Hz sequence pixels and actual preview-window snapshots; no human/physical-input acceptance or hard real-time guarantee.'))


def check(name, value, **detail):
    checks.append(dict(check=name, passed=bool(value), **detail)); report()


def call(tool, arguments, allow_error=False):
    global sequence
    sequence += 1; prefix = out/('%03d-' % sequence + tool)
    dump(prefix.with_suffix('.request.json'), arguments)
    result = subprocess.run([binary, 'call', tool, '--json', '-'], input=json.dumps(arguments), capture_output=True, text=True, env=env, timeout=20)
    prefix.with_suffix('.stdout.txt').write_text(result.stdout); prefix.with_suffix('.stderr.txt').write_text(result.stderr)
    dump(prefix.with_suffix('.exit.json'), dict(exitCode=result.returncode))
    value = json.loads(result.stdout)
    if result.returncode and not allow_error:
        raise RuntimeError(value)
    return value


def probe(*arguments):
    result = subprocess.run([str(root/'probe'), *map(str, arguments)], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError((arguments, result.stdout, result.stderr))
    return json.loads(result.stdout)


def wait(predicate, seconds=6):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.04)
    return False


def observe(window):
    # Initial AppKit window placement can settle after the fixture publishes its
    # first state. Reconcile read-only geometry; never retry a mutation here.
    deadline = time.monotonic()+3
    previous = None
    settled = False
    while time.monotonic() < deadline:
        current = next((w for w in probe('identity', fixture.pid).get('windows', []) if w['windowID'] == window), None)
        if current is not None and current == previous:
            settled = True
            break
        previous = current
        time.sleep(.1)
    dump(out/('window-'+str(window)+'-settled.json'), dict(settled=settled, window=previous))
    if not settled:
        raise AssertionError('Owned window geometry/title did not settle')
    for attempt in range(3):
        value = call('mac_observe', dict(pid=fixture.pid, processStartID=fixture_identity, windowID=window, screenshot=False), allow_error=True)
        if 'observation' in value:
            return value['observation']
        safe = value.get('code') == 'stale_observation' and value.get('disposition', {}).get('delivery') == 'not_delivered' and value.get('disposition', {}).get('retry') == 'safe'
        if not safe or attempt == 2:
            raise RuntimeError(value)
        time.sleep(.1)
    raise AssertionError('Unreachable observation attempt state')


def require_fixture_live(stage):
    actual = probe('identity', fixture.pid)
    value = read(root/'fixture-data/fixture.json')
    history = value.get('history', [])
    age = time.time()-history[-1]['unixTime'] if history else None
    if actual.get('processStartID') != fixture_identity or age is None or not -.05 <= age < 1.2:
        dump(out/'fixture-liveness-failure.json', dict(stage=stage, identity=actual, expectedIdentity=fixture_identity, state=value, ageSeconds=age))
        raise RuntimeError('Owned fixture exited or stopped updating during '+stage+'; this is fixture failure, not proof of product capture staleness')
    return value

def sample(label, intended, preview, count):
    windows = call('mac_windows', dict(pid=preview['pid']))['windows']
    panel = next(w for w in windows if w.get('title') == 'MacPilot Preview' and w.get('onScreen'))
    if not any(h['pid'] == preview['pid'] for h in hosts):
        hosts.append({k: preview[k] for k in ['pid', 'processStartID']})
    for index in range(count):
        before_fixture = require_fixture_live(label+'-before-'+str(index))
        current = call('mac_preview', dict(operation='status'))
        raw_path = out/(label+'-%02d-raw.png' % index); shutil.copy2(current['screenshot'], raw_path)
        raw = probe('decode', raw_path)
        panel_path = out/(label+'-%02d-panel.png' % index)
        rendered = probe('capture', preview['pid'], preview['processStartID'], panel['windowID'], panel_path)
        after_fixture = require_fixture_live(label+'-after-'+str(index))
        history = after_fixture.get('history', [])
        match = next((h for h in reversed(history) if h['sequence'] == rendered['sequence']), None)
        age = rendered['monotonic']-match['monotonic'] if match else None
        value = dict(stage=label, intendedTarget=intended, index=index, raw=raw, rendered=rendered,
                     renderedAgeSeconds=age, fixtureBeforeSequence=before_fixture.get('sequence'), fixtureAfterSequence=after_fixture.get('sequence'), productStatus=current, rawImage=raw_path.name, panelImage=panel_path.name)
        samples.append(value); report(); time.sleep(.1)
    relevant = [s for s in samples if s['stage'] == label]
    check(label+'_raw_pixels_follow_intended_target', all(s['raw']['target'] == intended for s in relevant), decoded=[s['raw']['target'] for s in relevant])
    check(label+'_visible_panel_pixels_follow_intended_target', all(s['rendered']['target'] == intended for s in relevant), decoded=[s['rendered']['target'] for s in relevant])
    transitions = len(set(s['rendered']['sequence'] for s in relevant))
    ordered = all((right['rendered']['sequence']-left['rendered']['sequence'])%1024 <= 50 for left, right in zip(relevant, relevant[1:]))
    check(label+'_visible_panel_has_multiple_real_sequence_transitions', transitions >= 3 and ordered, distinctSequences=transitions, ordered=ordered)
    ages = sorted(s['renderedAgeSeconds'] for s in relevant if s['renderedAgeSeconds'] is not None)
    p95 = ages[min(len(ages)-1, math.ceil(len(ages)*.95)-1)] if ages else None
    check(label+'_observed_panel_freshness_p95_under_one_second', len(ages) == len(relevant) and p95 is not None and -.05 <= min(ages) and p95 < 1, p95Seconds=p95)


try:
    (root/'fixture-data').mkdir()
    for name, source in [('fixture', FIXTURE), ('probe', PROBE)]:
        path = root/(name+'.swift'); path.write_text(source)
        command = ['xcrun', 'swiftc', '-parse-as-library', str(path), '-o', str(root/name)] if name == 'probe' else ['xcrun', 'swiftc', str(path), '-o', str(root/name)]
        compiled = subprocess.run(command, capture_output=True, text=True)
        (out/(name+'-build.log')).write_text(compiled.stdout+compiled.stderr); compiled.check_returncode()
    fixture_log = (out/'fixture.log').open('w')
    fixture = subprocess.Popen([str(root/'fixture'), str(root/'fixture-data')], stdout=fixture_log, stderr=fixture_log)
    assert wait(lambda: read(root/'fixture-data/fixture.json').get('pid') == fixture.pid, 10)
    fixture_identity = probe('identity', fixture.pid)['processStartID']
    windows = read(root/'fixture-data/fixture.json')['windows']; window_a = windows[0]['windowID']; window_b = windows[1]['windowID']
    observation = observe(window_a)
    preview_a = call('mac_preview', dict(operation='start', observation=observation['id']))
    check('initial_start_reports_window_a', preview_a.get('windowID') == window_a and preview_a.get('targetPID') == fixture.pid
        and preview_a.get('targetStartID') == fixture_identity and preview_a.get('observationID') == observation['id']
        and preview_a.get('frameCount', 0) > 0, requested=window_a, returned=preview_a)
    sample('target_a', 1, preview_a, a.samples)
    same = call('mac_preview', dict(operation='start', observation=observation['id']))
    check('same_target_start_reuses_exact_host_and_launch', same.get('pid') == preview_a['pid']
        and same.get('processStartID') == preview_a['processStartID'] and same.get('launchSequence') == preview_a.get('launchSequence'))
    call('mac_preview', dict(operation='pause'))
    hidden = call('mac_preview', dict(operation='hide'))
    preserved = call('mac_preview', dict(operation='start', observation=observation['id']))
    check('same_target_start_preserves_hidden_paused_state', preserved.get('pid') == preview_a['pid']
        and preserved.get('processStartID') == preview_a['processStartID'] and preserved.get('paused') and not preserved.get('visible'))
    previous_host = probe('identity', preview_a['pid'])
    observation_b = observe(window_b)
    preview_b = call('mac_preview', dict(operation='start', observation=observation_b['id']))
    check('same_state_start_b_reports_requested_window_b', preview_b.get('windowID') == window_b
        and preview_b.get('targetPID') == fixture.pid and preview_b.get('targetStartID') == fixture_identity
        and preview_b.get('observationID') == observation_b['id'] and preview_b.get('frameCount', 0) > 0
        and preview_b.get('visible') and not preview_b.get('paused') and preview_b.get('launchSequence') != preview_a.get('launchSequence'), requested=window_b, returned=preview_b)
    old_after = probe('identity', preview_a['pid'])
    check('retarget_confirms_previous_host_exit_and_windows_absent', old_after.get('processStartID') != preview_a['processStartID']
        and not set(previous_host.get('windowIDs', [])).intersection(old_after.get('windowIDs', [])), before=previous_host, after=old_after)
    sample('target_b', 2, preview_b, a.samples)
    completed = True
except BaseException as error:
    failures.append(repr(error)); (out/'failure.log').write_text(traceback.format_exc())
finally:
    report()
    def cleanup(name, action):
        try:
            action()
        except BaseException as error:
            cleanup_errors.append(dict(operation=name, error=repr(error))); (out/('cleanup-'+str(len(cleanup_errors))+'.log')).write_text(traceback.format_exc())
    def stop_owned_preview():
        status = read(root/'state/preview-status.json')
        if status.get('pid') and probe('identity', status['pid']).get('processStartID') == status.get('processStartID'):
            call('mac_preview', dict(operation='stop'))
            assert wait(lambda: probe('identity', status['pid']).get('processStartID') != status['processStartID'], 4), status
    def stop_owned_overlay():
        overlay = read(root/'state/overlay-status.json')
        if not overlay.get('pid'):
            return
        before = probe('identity', overlay['pid'])
        if before.get('processStartID') == overlay.get('processStartID'):
            receipt = call('mac_cursors', dict(operation='stop'))
            assert wait(lambda: probe('identity', overlay['pid']).get('processStartID') != overlay['processStartID'], 4), overlay
            after = probe('identity', overlay['pid'])
            dump(out/'overlay-cleanup.json', dict(before=before, after=after, receipt=receipt))
            assert not set(before.get('windowIDs', [])).intersection(after.get('windowIDs', [])), (before, after)
    if (root/'probe').exists():
        cleanup('owned preview stop and exact exit', stop_owned_preview)
        for host in hosts:
            cleanup('all owned preview generations exited', lambda host=host: (_ for _ in ()).throw(AssertionError(host))
                if not wait(lambda: probe('identity', host['pid']).get('processStartID') != host['processStartID'], 4) else None)
        # Exit is verified while the target still lives. Target termination is
        # never accepted as evidence that explicit feedback cleanup worked.
        cleanup('owned desktop feedback stop and exact exit', stop_owned_overlay)
    elif read(root/'state/preview-status.json').get('pid') or read(root/'state/overlay-status.json').get('pid'):
        cleanup_errors.append(dict(operation='owned helper cleanup', error='Identity probe unavailable; process exit is unverified'))
    if fixture and fixture.poll() is None:
        cleanup('owned fixture terminate', fixture.terminate); cleanup('owned fixture exact exit', lambda: fixture.wait(timeout=5))
    if 'fixture_log' in locals():
        fixture_log.close()
    report()
if failures or cleanup_errors or not completed or not all(c['passed'] for c in checks):
    raise SystemExit(1)
print((out/'report.json').read_text())
