#!/usr/bin/python3
"""Development-only acceptance harness. Uses stdlib and synthetic fixture data."""
import json
import hashlib
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import time
import tempfile

skill = Path(__file__).resolve().parent.parent
binary = skill / "bin/MacPilot.app/Contents/MacOS/macpilot"
# Build, install, sign, and strictly verify the exact binary exercised below.
subprocess.run([str(skill / "scripts/build.sh")], check=True)
subprocess.run(["/usr/bin/xcrun","swift","build","--package-path",str(skill/"tool"),"--product","macpilot-fixture"],check=True)
fixture_dir = Path(subprocess.check_output(["/usr/bin/xcrun","swift","build","--package-path",str(skill/"tool"),"--show-bin-path"],text=True).strip())
fixture = fixture_dir / "macpilot-fixture"
out = skill / "evidence/runtime-current"
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True, exist_ok=True, mode=0o700)
env = os.environ.copy()
private_state = tempfile.TemporaryDirectory(prefix="macpilot-runtime-")
state_dir = Path(private_state.name) / "state"
env["MACPILOT_STATE_DIR"] = str(state_dir)
env["MACPILOT_FIXTURE_DIR"] = str(out / "fixture")
sequence = 0
checks = []
process_start_ids = {}

def call(name, args, expected_error=None):
    global sequence
    sequence += 1
    request = json.dumps(args, ensure_ascii=False)
    (out / f"{sequence:02d}-{name}-request.json").write_text(request)
    command = [str(binary), "call", name, "--json", "-"]
    # Enforce the no-network runtime property independently of source inspection.
    if Path("/usr/bin/sandbox-exec").exists():
        command = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"] + command
    p = subprocess.run(command, input=request, text=True, capture_output=True, env=env, timeout=20)
    (out / f"{sequence:02d}-{name}.json").write_text(p.stdout)
    (out / f"{sequence:02d}-{name}.stderr.log").write_text(p.stderr)
    result = json.loads(p.stdout)
    if expected_error:
        accepted=[expected_error] if isinstance(expected_error,str) else expected_error
        assert p.returncode == 2 and result.get("code") in accepted, result
    else:
        assert p.returncode == 0, result
    return result

def check(name, condition, detail=None):
    checks.append({"check": name, "passed": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(name + ": " + str(detail))

def state():
    return json.loads((out / "fixture/state.json").read_text())

def wait_state(predicate, seconds=2):
    deadline=time.monotonic()+seconds
    while time.monotonic() < deadline:
        if predicate(state()): return True
        time.sleep(0.05)
    return False

def observe(pid, screenshot=False):
    return call("mac_observe", {"pid": pid, "processStartID": process_start_ids[pid], "screenshot": screenshot})["observation"]

def node(o, identifier):
    return next(n for n in o["nodes"] if n["identifier"] == identifier)

def action(o, n, operation, **kwargs):
    return call("mac_ax", {"observation":o["id"], "node":n["id"], "operation":operation, **kwargs})

log = (out / "fixture-process.log").open("w")
p = subprocess.Popen([str(fixture)], env=env, stdout=log, stderr=log)
p2 = None
preview = None
source_paths = list((skill / "tool/Sources").rglob("*.swift")) + [skill / "tool/Package.swift", skill / "scripts/build.sh", skill / "assets/app-icon.png"]
report = {
    "checks":checks,
    "networkPolicy":"sandbox deny network*",
    "fixturePID":p.pid,
    "installedBinary": {
        "path": str(binary),
        "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "builtAfterMaintainedSources": binary.stat().st_mtime >= max(path.stat().st_mtime for path in source_paths),
        "buildPolicy": "scripts/build.sh rebuilt, installed, ad-hoc signed, and strictly verified this binary before runtime checks"
    }
}
try:
    for _ in range(60):
        if (out / "fixture/state.json").exists() and state().get("pid") == p.pid:
            break
        if p.poll() is not None:
            raise RuntimeError("Fixture exited; inspect fixture-process.log")
        time.sleep(0.1)
    doctor = call("mac_doctor", {})
    check("installed_binary_rebuilt_from_current_sources", report["installedBinary"]["builtAfterMaintainedSources"], report["installedBinary"])
    check("required_permissions", all(doctor["permissions"][k] for k in ("accessibility","screenCapture","postEvent")), doctor["permissions"])
    apps = call("mac_apps", {})
    fixture_app = next(app for app in apps["apps"] if app["pid"] == p.pid)
    process_start_id = fixture_app.get("processStartID")
    check("process_identity_exposed", bool(process_start_id), fixture_app)
    process_start_ids[p.pid] = process_start_id
    call("mac_app", {"pid":p.pid, "processStartID":process_start_id+"0", "action":"hide"}, expected_error="stale_app_identity")
    call("mac_menu", {"pid":p.pid, "processStartID":process_start_id+"0", "operation":"press", "titlePath":["Edit","Select All"]}, expected_error="stale_app_identity")
    call("mac_observe", {"pid":p.pid, "processStartID":process_start_id+"0", "screenshot":False}, expected_error="stale_app_identity")
    checks.append({"check":"stale_process_identity_rejected_before_observation_or_mutation","passed":True})
    call("mac_capture", {"displayID":4294967295,"maxDimension":64}, expected_error="display_unavailable")
    checks.append({"check":"display_capture_rejects_inactive_display_before_capture","passed":True})
    scripted = call("mac_script", {"language":"applescript", "source":"return 6 * 7", "timeoutMs":5000, "maxOutputBytes":4096})
    check("bounded_osascript_stdin", scripted["status"] == "script_completed" and scripted["stdout"].strip() == "42", scripted)
    time.sleep(0.4)
    call("mac_windows", {"pid":p.pid})
    o = observe(p.pid, screenshot=True)
    check("window_AX_and_screen_capture", len(o["nodes"]) > 5 and Path(o["screenshot"]).is_file(), {"nodes":len(o["nodes"]),"image":o["screenshot"],"coverage":o["coverage"]})
    check("secure_value_redacted", "synthetic-secret" not in json.dumps(o), None)
    hidden = call("mac_app", {"pid":p.pid, "processStartID":process_start_id, "action":"hide", "timeoutMs":3000})
    check("owned_app_hide_verified", hidden["status"] == "app_state_verified" and hidden["hidden"], hidden)
    shown = call("mac_app", {"pid":p.pid, "processStartID":process_start_id, "action":"unhide", "timeoutMs":3000})
    check("owned_app_unhide_verified", shown["status"] == "app_state_verified" and not shown["hidden"], shown)
    active = call("mac_app", {"pid":p.pid, "processStartID":process_start_id, "action":"activate", "timeoutMs":3000})
    check("owned_app_activation_verified", active["status"] == "app_state_verified" and active["active"], active)
    o = observe(p.pid, screenshot=True)
    found = call("mac_find", {"observation":o["id"], "identifier":"literal-text", "maxResults":4})
    check("bounded_snapshot_find", found["matchCount"] == 1 and found["matches"][0]["identifier"] == "literal-text", found)
    field_node = node(o,"literal-text")
    waited = call("mac_wait", {"observation":o["id"], "node":field_node["id"], "equals":"초기 값", "timeoutMs":500, "pollMs":50})
    check("bounded_live_text_wait", waited["status"] == "predicate_verified" and waited["matches"], waited)
    timed = call("mac_wait", {"observation":o["id"], "node":field_node["id"], "contains":"존재하지 않는 후조건", "timeoutMs":100, "pollMs":50})
    check("bounded_wait_timeout_reported", timed["status"] == "predicate_timeout" and not timed["matches"], timed)
    menu = call("mac_menu", {"pid":p.pid, "operation":"list", "maxItemsPerLevel":64})
    check("bounded_top_level_menu_list", menu["scope"] == "complete_top_level_menu_bar" and any(item["title"] == "Edit" for item in menu["items"]), menu)
    selected_before = state()["events"].get("selectAll",0)
    pressed = call("mac_menu", {"pid":p.pid, "processStartID":process_start_id, "operation":"press", "titlePath":["Edit","Select All"], "maxItemsPerLevel":64})
    check("exact_menu_path_action_received", pressed["status"] == "action_requested" and wait_state(lambda s:s["events"].get("selectAll",0) > selected_before), state())
    frame = o["windowFrame"]
    state_result = call("mac_window", {"observation":o["id"], "operation":"state"})
    check("window_state_bound_to_observation", state_result["state"]["exists"] and state_result["state"]["title"] == "MacPilot 검증 전용", state_result)
    moved = call("mac_window", {"observation":o["id"], "operation":"move", "x":frame["x"]+8, "y":frame["y"]+8})
    check("window_move_verified", moved["status"] == "moved_verified", moved)
    o = observe(p.pid, screenshot=False)
    resized = call("mac_window", {"observation":o["id"], "operation":"resize", "width":frame["width"]+16, "height":frame["height"]+16})
    check("window_resize_verified", resized["status"] == "resized_verified", resized)
    o = observe(p.pid, screenshot=False)
    raised = call("mac_window", {"observation":o["id"], "operation":"raise"})
    check("window_raise_is_explicitly_unverified", raised["status"] == "requested_unverified", raised)
    o = observe(p.pid, screenshot=False)
    minimized = call("mac_window", {"observation":o["id"], "operation":"minimize"})
    check("window_minimize_verified", minimized["status"] == "minimized_verified", minimized)
    o = observe(p.pid, screenshot=False)
    unminimized = call("mac_window", {"observation":o["id"], "operation":"unminimize"})
    check("window_unminimize_verified", unminimized["status"] == "unminimized_verified", unminimized)
    o = observe(p.pid, screenshot=True)
    secure = node(o,"secure-text")
    call("mac_ax", {"observation":o["id"],"node":secure["id"],"operation":"set_value","text":"forbidden"}, expected_error="invalid_node")
    checks.append({"check":"secure_input_node_rejected","passed":True})
    disabled = node(o,"disabled")
    call("mac_ax", {"observation":o["id"],"node":disabled["id"],"operation":"action"}, expected_error="disabled_control")
    checks.append({"check":"disabled_control_rejected","passed":True})
    pointer = call("mac_pointer", {"observation":o["id"],"x":0.6,"y":0.75,"space":"normalized"})
    check("virtual_pointer_posts_zero_events", pointer["eventsPosted"] == 0, pointer)
    check("virtual_pointer_does_not_move_system_cursor", pointer["systemCursorBefore"] == pointer["systemCursorAfter"])
    ocr = call("mac_ocr", {"observation":o["id"],"languages":["ko-KR","en-US"]})
    check("local_OCR_read_fixture", any("입력" in t["text"] for t in ocr["text"]), ocr["text"])
    action(o, node(o,"increment"), "action")
    time.sleep(0.25)
    check("AX_button_action_received", state()["buttonCount"] == 1, state())
    call("mac_ax", {"observation":o["id"],"node":node(o,"increment")["id"],"operation":"action"}, expected_error="stale_observation")
    checks.append({"check":"consumed_observation_rejected","passed":True})
    o = observe(p.pid)
    result = action(o,node(o,"literal-text"),"set_value",text="독립 로컬 입력 😀")
    time.sleep(0.25)
    check("AX_value_round_trip", result["status"] == "value_verified" and state()["text"] == "독립 로컬 입력 😀", state())
    o = observe(p.pid)
    result = action(o,node(o,"literal-text"),"select_range",start=0,length=2)
    check("UTF16_selection_round_trip",result["status"] == "range_verified",result)
    o = observe(p.pid)
    field = node(o,"literal-text")
    if not field["focused"]:
        action(o,field,"focus"); o = observe(p.pid); field = node(o,"literal-text")
    call("mac_key",{"observation":o["id"],"node":field["id"],"key":"a","modifiers":["command"]})
    check("PID_command_shortcut_received",wait_state(lambda s:s["events"].get("selectAll",0) > 0 and s["selection"]["length"] > 2),state())
    o = observe(p.pid)
    call("mac_type",{"observation":o["id"],"node":node(o,"literal-text")["id"],"text":"한글 😀 e\u0301"})
    check("PID_Unicode_keyboard_received",wait_state(lambda s:s["text"] == "한글 😀 e\u0301"),state())
    o = observe(p.pid)
    verified=call("mac_verify",{"observation":o["id"],"node":node(o,"literal-text")["id"],"equals":"한글 😀 e\u0301"})
    check("explicit_predicate",verified["matches"],verified)
    o = observe(p.pid)
    action(o,node(o,"arm-focus-shift"),"action")
    check("focus_shift_fixture_armed",wait_state(lambda s:s["focusShiftArmed"]),state())
    o = observe(p.pid)
    long_text="x" * 60
    interrupted=call("mac_type",{"observation":o["id"],"node":node(o,"literal-text")["id"],"text":long_text})
    shifted_state=state()
    check("typing_stops_when_focus_moves_to_secure_input",
          interrupted["status"] == "dispatch_interrupted" and 0 < interrupted["eventsPosted"] < 6
          and shifted_state["events"].get("focusShiftedToSecure",0) > 0
          and shifted_state["secureUnchanged"] and long_text not in shifted_state["text"]
          and interrupted["reasonCode"] in ("focus_mismatch","secure_input"),
          {"dispatch":interrupted,"state":shifted_state})
    o = observe(p.pid)
    action(o,node(o,"literal-text"),"focus")
    # Cover the target with a second owned fixture, so background claims are measured.
    env2=env.copy(); env2["MACPILOT_FIXTURE_DIR"]=str(out/"foreground-fixture")
    p2=subprocess.Popen([str(fixture)],env=env2,stdout=log,stderr=log)
    for _ in range(60):
        path=out/"foreground-fixture/state.json"
        if path.exists() and json.loads(path.read_text()).get("pid") == p2.pid: break
        if p2.poll() is not None: raise RuntimeError("Second fixture exited")
        time.sleep(0.1)
    check("background_target_established",wait_state(lambda s:not s["active"]),state())
    o=observe(p.pid)
    button=node(o,"increment"); rect=button["frame"]
    pointer_state=state_dir/"pointer.json"
    if pointer_state.exists():
        pointer_state.unlink() if pointer_state.is_file() else shutil.rmtree(pointer_state)
    pointer_state.mkdir()
    clicked=call("mac_click",{"observation":o["id"],"x":rect["x"]-o["windowFrame"]["x"]+rect["width"]/2,"y":rect["y"]-o["windowFrame"]["y"]+rect["height"]/2})
    pointer_state.rmdir()
    check("background_virtual_coordinate_AX_click",wait_state(lambda s:s["buttonCount"] == 2 and not s["active"]),state())
    check("background_AX_click_preserves_cursor",clicked["eventsPosted"] == 0 and clicked["systemCursorBefore"] == clicked["systemCursorAfter"],clicked)
    check("post_dispatch_pointer_failure_is_a_warning",clicked["status"] == "action_requested" and "warning" in clicked,clicked)
    o=observe(p.pid)
    replaced=action(o,node(o,"literal-text"),"set_value",text="백그라운드 😀")
    check("background_AX_text_verified",wait_state(lambda s:s["text"] == "백그라운드 😀" and not s["active"]),state())
    o=observe(p.pid)
    field=node(o,"literal-text")
    call("mac_key",{"observation":o["id"],"node":field["id"],"key":"a","modifiers":["command"]})
    time.sleep(0.15)
    o=observe(p.pid)
    call("mac_type",{"observation":o["id"],"node":node(o,"literal-text")["id"],"text":"별도 입력 🚀"})
    time.sleep(0.25)
    foreground_state=json.loads((out/"foreground-fixture/state.json").read_text())
    report["backgroundProcessKeyboard"]={"accepted":state()["text"] == "별도 입력 🚀","target":state(),"foreground":foreground_state}
    check("PID_keyboard_never_reaches_other_fixture",foreground_state["text"] == "초기 값",foreground_state)
    # PID mouse support is measured, not assumed. The result is reported separately.
    mouse = {}
    for tool, extra in [("mac_click",{}),("mac_drag",{"toX":250,"toY":350}),("mac_scroll",{"vertical":-3})]:
        o=observe(p.pid)
        r=call(tool,{"observation":o["id"],"x":100,"y":350,"route":"process",**extra})
        time.sleep(0.2)
        mouse[tool]={"dispatch":r,"fixtureEvents":state()["events"].copy()}
    report["processMouse"]=mouse
    o=observe(p.pid)
    call("mac_click",{"observation":o["id"],"x":100,"y":350,"route":"global"},expected_error="foreground_mismatch")
    checks.append({"check":"global_input_rejects_background_target","passed":True})
    o=observe(p.pid)
    call("mac_activate",{"observation":o["id"]})
    check("explicit_activation_verified",wait_state(lambda s:s["active"]),state())
    # Global path stays inside the owned fixture and does not target any user document.
    o=observe(p.pid)
    r=call("mac_click",{"observation":o["id"],"x":100,"y":350,"route":"global"})
    time.sleep(0.2)
    check("global_click_received",state()["events"].get("mouseDown",0) > 0,state())
    report["globalMouse"]=r
    o=observe(p.pid)
    call("mac_drag",{"observation":o["id"],"x":100,"y":350,"toX":250,"toY":350,"route":"global"})
    check("global_drag_received",wait_state(lambda s:s["events"].get("mouseDragged",0) > 0),state())
    o=observe(p.pid)
    call("mac_scroll",{"observation":o["id"],"x":100,"y":350,"vertical":-3,"route":"global"})
    check("global_scroll_received",wait_state(lambda s:s["events"].get("scrollWheel",0) > 0),state())
    # Cancel a long raw drag after mouse-down. The controller must post the
    # pending mouse-up before it releases the MCP capacity slot.
    o=observe(p.pid)
    pointer_events_before=state()["events"].copy()
    cancel_rpc=subprocess.Popen([str(binary),"mcp"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                text=True,bufsize=1,env=env)
    try:
        cancel_rpc.stdin.write(json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25"}})+"\n")
        cancel_rpc.stdin.flush()
        readable,_,_=select.select([cancel_rpc.stdout],[],[],2)
        cancel_initialize=json.loads(cancel_rpc.stdout.readline()) if readable else None
        check("MCP_cancel_fixture_initialized",cancel_initialize is not None and cancel_initialize.get("id") == 1,
              cancel_initialize)
        cancel_request={"jsonrpc":"2.0","id":101,"method":"tools/call","params":{"name":"mac_drag","arguments":{
            "observation":o["id"],"x":100,"y":350,"toX":250,"toY":350,"duration":2.0,"route":"global"}}}
        cancel_rpc.stdin.write(json.dumps(cancel_request)+"\n"); cancel_rpc.stdin.flush()
        time.sleep(0.16)
        cancel_rpc.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/cancelled","params":{"requestId":101}})+"\n")
        cancel_rpc.stdin.flush()
        balanced=wait_state(lambda s:
            s["events"].get("mouseDown",0) > pointer_events_before.get("mouseDown",0) and
            s["events"].get("mouseUp",0) > pointer_events_before.get("mouseUp",0),seconds=2)
        cancel_rpc.stdin.write(json.dumps({"jsonrpc":"2.0","id":102,"method":"tools/call","params":{"name":"mac_doctor","arguments":{}}})+"\n")
        cancel_rpc.stdin.flush()
        readable,_,_=select.select([cancel_rpc.stdout],[],[],2)
        followup=json.loads(cancel_rpc.stdout.readline()) if readable else None
        after_events=state()["events"]
        check("cancelled_raw_drag_posts_balanced_release_and_frees_capacity",
              balanced and after_events.get("mouseDown",0)-pointer_events_before.get("mouseDown",0) == 1
              and after_events.get("mouseUp",0)-pointer_events_before.get("mouseUp",0) == 1
              and followup is not None and followup.get("id") == 102
              and not followup.get("result",{}).get("isError",False),
              {"before":pointer_events_before,"after":after_events,"followup":followup})
        focus_observation=observe(p.pid)
        action(focus_observation,node(focus_observation,"literal-text"),"focus")
        key_observation=observe(p.pid)
        key_events_before=state()["events"].copy()
        cancel_type={"jsonrpc":"2.0","id":103,"method":"tools/call","params":{"name":"mac_type","arguments":{
            "observation":key_observation["id"],"node":node(key_observation,"literal-text")["id"],"text":"z"*200}}}
        cancel_rpc.stdin.write(json.dumps(cancel_type)+"\n"); cancel_rpc.stdin.flush()
        time.sleep(0.12)
        cancel_rpc.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/cancelled","params":{"requestId":103}})+"\n")
        cancel_rpc.stdin.flush()
        time.sleep(0.15)
        cancel_rpc.stdin.write(json.dumps({"jsonrpc":"2.0","id":104,"method":"tools/call","params":{"name":"mac_doctor","arguments":{}}})+"\n")
        cancel_rpc.stdin.flush()
        readable,_,_=select.select([cancel_rpc.stdout],[],[],2)
        key_followup=json.loads(cancel_rpc.stdout.readline()) if readable else None
        key_events_after=state()["events"]
        key_down_delta=key_events_after.get("keyDown",0)-key_events_before.get("keyDown",0)
        key_up_delta=key_events_after.get("keyUp",0)-key_events_before.get("keyUp",0)
        check("cancelled_raw_key_sequence_is_balanced_and_frees_capacity",
              key_down_delta > 0 and key_down_delta == key_up_delta
              and key_followup is not None and key_followup.get("id") == 104
              and not key_followup.get("result",{}).get("isError",False),
              {"before":key_events_before,"after":key_events_after,"followup":key_followup})
    finally:
        cancel_rpc.terminate()
        try: cancel_rpc.wait(timeout=3)
        except subprocess.TimeoutExpired: cancel_rpc.kill(); cancel_rpc.wait()
    older=observe(p.pid)
    o=observe(p.pid)
    try:
        action(o,node(o,"show-sheet"),"action")
    except AssertionError as error:
        if not error.args or not isinstance(error.args[0],dict) or error.args[0].get('code') != 'ax_outcome_uncertain':
            raise
        report.setdefault('reconciledOutcomes',[]).append(error.args[0])
    check("owned_modal_fixture_opened",wait_state(lambda s:s["sheetOpen"]),state())
    call("mac_ax",{"observation":older["id"],"node":node(older,"increment")["id"],"operation":"action"},expected_error=["modal_sheet","stale_observation"])
    checks.append({"check":"new_modal_rejects_old_underlying_control","passed":True})
    o=observe(p.pid)
    close=next(n for n in o["nodes"] if n["title"] == "닫기" and "AXPress" in n["actions"])
    try:
        action(o,close,"action")
    except AssertionError as error:
        if not error.args or not isinstance(error.args[0],dict) or error.args[0].get('code') != 'ax_outcome_uncertain':
            raise
        report.setdefault('reconciledOutcomes',[]).append(error.args[0])
    check("modal_child_action_allowed",wait_state(lambda s:not s["sheetOpen"] and s["events"].get("sheetClosed",0) == 1),state())
    o=observe(p.pid)
    call("mac_pointer",{"observation":o["id"],"x":10000,"y":350},expected_error="out_of_bounds")
    checks.append({"check":"coordinate_boundary_rejected","passed":True})
    o=observe(p.pid,screenshot=True)
    r=call("mac_pointer",{"observation":o["id"],"x":0.14,"y":0.5,"space":"normalized"})
    report["finalSnapshot"]=r.get("preview")
    foreground_before=call("mac_doctor",{})["foregroundPID"]
    preview=subprocess.Popen([str(binary),"preview",o["id"]],env=env,stdout=log,stderr=log)
    time.sleep(0.4)
    preview_windows=call("mac_windows",{"pid":preview.pid})["windows"]
    foreground_after=call("mac_doctor",{})["foregroundPID"]
    check("preview_panel_visible_without_activation",any(w["onScreen"] for w in preview_windows) and foreground_before == foreground_after, {"windows":preview_windows,"foregroundBefore":foreground_before,"foregroundAfter":foreground_after})
    preview.terminate();preview.wait(timeout=3);preview=None
    # A new process exercises CLI input errors and MCP framing without a model host.
    messages=[{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25"}},
              {"jsonrpc":"2.0","method":"notifications/initialized"},
              {"jsonrpc":"2.0","id":2,"method":"tools/list"},
              {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"mac_doctor"}},
              {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"mac_windows","arguments":{"pid":True}}},
              {"jsonrpc":"2.0","id":5,"method":"ping"}]
    rpc=subprocess.run([str(binary),"mcp"],input="\n".join(json.dumps(m) for m in messages)+"\n",text=True,capture_output=True,env=env,timeout=10)
    (out/"mcp-responses.jsonl").write_text(rpc.stdout); (out/"mcp.stderr.log").write_text(rpc.stderr)
    responses=[json.loads(l) for l in rpc.stdout.splitlines()]
    expected_tools={"mac_doctor","mac_apps","mac_windows","mac_launch","mac_app","mac_open","mac_reveal","mac_trash",
                    "mac_clipboard_read","mac_clipboard_write","mac_shortcuts","mac_script","mac_permission","mac_observe",
                    "mac_activate","mac_ax","mac_pointer","mac_click","mac_drag","mac_scroll","mac_key","mac_type","mac_find",
                    "mac_ocr","mac_wait","mac_verify","mac_capture","mac_menu","mac_window"}
    actual_tools={tool["name"] for tool in responses[1]["result"]["tools"]}
    check("MCP_handshake_tools_call_and_error",rpc.returncode == 0 and [r["id"] for r in responses] == [1,2,3,4,5]
          and expected_tools.issubset(actual_tools) and responses[3]["result"]["isError"],
          {"ids":[r["id"] for r in responses],"expected":sorted(expected_tools),"actual":sorted(actual_tools)})
    live_rpc=subprocess.Popen([str(binary),"mcp"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,bufsize=1,env=env)
    try:
        live_rpc.stdin.write(json.dumps(messages[0])+"\n"); live_rpc.stdin.flush()
        readable,_,_=select.select([live_rpc.stdout],[],[],2)
        live_response=json.loads(live_rpc.stdout.readline()) if readable else None
        check("MCP_live_pipe_responds_without_stdin_EOF",live_response is not None and live_response.get("id") == 1,
              live_response)
        live_rpc.stdin.write("{invalid json\n"); live_rpc.stdin.flush()
        readable,_,_=select.select([live_rpc.stdout],[],[],2)
        parse_response=json.loads(live_rpc.stdout.readline()) if readable else None
        check("MCP_live_pipe_flushes_parse_errors",parse_response is not None and
              parse_response.get("error",{}).get("code") == -32700,parse_response)
    finally:
        live_rpc.terminate()
        try: live_rpc.wait(timeout=3)
        except subprocess.TimeoutExpired: live_rpc.kill(); live_rpc.wait()
    audit_rows=[json.loads(line) for line in (state_dir/"audit.jsonl").read_text().splitlines()]
    observation_bound={"mac_activate","mac_ax","mac_pointer","mac_click","mac_drag","mac_scroll","mac_key","mac_type","mac_find","mac_ocr","mac_wait","mac_verify","mac_window"}
    bound_rows=[row for row in audit_rows if row["tool"] in observation_bound]
    check("audit_records_pid_for_observation_bound_success_and_failure",
          bool(bound_rows) and all(row.get("pid") == p.pid for row in bound_rows),bound_rows)
    o=observe(p.pid,screenshot=False)
    closed=call("mac_window",{"observation":o["id"],"operation":"close"})
    check("owned_window_close_verified",closed["status"] == "closed_verified" and not closed["state"]["exists"],closed)
    report["status"]="passed"
except Exception as e:
    report["status"]="failed"; report["failure"]=repr(e)
    raise
finally:
    if preview is not None and preview.poll() is None:
        preview.terminate()
        try: preview.wait(timeout=3)
        except subprocess.TimeoutExpired: preview.kill();preview.wait()
    if p2 is not None and p2.poll() is None:
        p2.terminate()
        try: p2.wait(timeout=3)
        except subprocess.TimeoutExpired: p2.kill(); p2.wait()
    if p.poll() is None:
        p.terminate()
        try: p.wait(timeout=3)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
    for status in list(state_dir.rglob('overlay-status.json'))+list(state_dir.rglob('preview-status.json')):
        try:
            host=json.loads(status.read_text())
            subprocess.run([str(binary),'call','mac_app','--json','-'],input=json.dumps(dict(pid=host['pid'],processStartID=host['processStartID'],action='force_terminate')),text=True,capture_output=True,env=env,timeout=5)
        except (OSError,ValueError,subprocess.TimeoutExpired):
            pass
    time.sleep(.2)
    private_state.cleanup()
    log.close()
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
