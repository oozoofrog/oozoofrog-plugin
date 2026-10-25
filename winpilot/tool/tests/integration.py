"""자체 fixture의 네이티브 창과 MCP 계약을 검증한다. 사용자 문서는 변경하지 않는다."""
import argparse
import base64
import ctypes
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(os.environ.get("WINDOWS_PILOT_EXE", str(ROOT / "artifacts/app/windows-pilot.exe")))
CREATE_NO_WINDOW = 0x08000000


class Client:
    def __init__(self, command=None):
        self.p = subprocess.Popen(command or [str(EXE), "--stdio"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=CREATE_NO_WINDOW)
        self.messages = queue.Queue()
        self.counter = 0
        self.saved = {}
        threading.Thread(target=self._read, daemon=True).start()
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pilot-test", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _read(self):
        for line in self.p.stdout:
            try:
                self.messages.put(json.loads(line))
            except Exception as error:
                self.messages.put({"reader_error": str(error)})

    def send(self, value):
        self.p.stdin.write(json.dumps(value, ensure_ascii=False) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params):
        self.counter += 1
        request_id = self.counter
        self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        while request_id not in self.saved:
            reply = self.messages.get(timeout=20)
            if "id" not in reply:
                raise AssertionError(reply)
            self.saved[reply["id"]] = reply
        reply = self.saved.pop(request_id)
        assert "error" not in reply, reply
        return reply["result"]

    def tool(self, name, args=None, allow_error=False):
        r = self.rpc("tools/call", {"name": name, "arguments": args or {}})
        text = json.loads(r["content"][0]["text"])
        if not allow_error:
            assert not r.get("isError"), text
        return text, r

    def wait(self, job_id):
        for _ in range(150):
            state, _ = self.tool("job_status", {"job_id": job_id})
            if state["state"] == "finished":
                return state["result"]
            time.sleep(.05)
        raise AssertionError("작업이 끝나지 않았습니다.")

    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close()
            try:
                self.p.wait(timeout=12)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait()


def inspect_targets(names):
    client = Client()
    results = []
    try:
        listing, _ = client.tool("windows_list")
        for window in listing["windows"]:
            if not any(n.casefold() in (window["process"] + " " + window["title"]).casefold() for n in names):
                continue
            observation, raw = client.tool("window_observe", {"window_id": window["window_id"]})
            image = next((c for c in raw["content"] if c["type"] == "image"), None)
            if image:
                path = ROOT / "artifacts" / f"target-{window['pid']}.png"
                path.write_bytes(base64.b64decode(image["data"]))
            results.append({"process": window["process"], "title": window["title"], "pid": window["pid"],
                            "capture_status": observation["capture_status"], "capture": observation.get("capture"),
                            "accessibility_status": observation["accessibility_status"], "element_count": len(observation["elements"]),
                            "accessibility_message": observation.get("accessibility_message"),
                            "image": str(path) if image else None})
        return {"mode": "read_only_target_inspection", "matches": results, "requested": names}
    finally:
        client.close()


def integration():
    fixtures = []
    client = None
    checks = []
    try:
        for name in ("A", "B"):
            fixtures.append(subprocess.Popen([str(EXE), "--fixture", name], creationflags=CREATE_NO_WINDOW))
        client = Client()
        tools = client.rpc("tools/list", {})["tools"]
        assert len(tools) == 7
        action_types = next(t for t in tools if t["name"] == "action_run")["inputSchema"]["properties"]["type"]["enum"]
        assert "click" in action_types and "drag" in action_types
        checks.append("MCP 초기화와 7개 도구 발견")
        windows = []
        for _ in range(40):
            listing, _ = client.tool("windows_list")
            windows = [w for w in listing["windows"] if w["pid"] in [p.pid for p in fixtures]]
            if len(windows) == 2:
                break
            time.sleep(.1)
        assert len(windows) == 2, "fixture 창 2개를 찾지 못했습니다."
        windows.sort(key=lambda w: w["title"])
        a, b = windows
        u32 = ctypes.windll.user32
        u32.GetForegroundWindow.restype = ctypes.c_void_p
        time.sleep(.3)
        foreground = u32.GetForegroundWindow()
        class Point(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        def pointer_position():
            point = Point()
            assert u32.GetCursorPos(ctypes.byref(point))
            return point.x, point.y
        initial_pointer = pointer_position()
        if foreground == a["hwnd"]:
            a, b = b, a
            windows = [a, b]
        assert foreground and foreground != a["hwnd"], "검증 대상이 백그라운드여야 합니다."
        snapshots = []
        for window in windows:
            o, raw = client.tool("window_observe", {"window_id": window["window_id"]})
            assert o["accessibility_status"] == "observed", o
            assert o["capture_status"] == "captured", o
            assert o["capture"]["coordinate_mapping_valid"], o["capture"]
            image = next(c for c in raw["content"] if c["type"] == "image")
            (ROOT / "artifacts" / (window["title"][-1] + ".png")).write_bytes(base64.b64decode(image["data"]))
            snapshots.append(o)
        assert u32.GetForegroundWindow() == foreground
        checks.append("WGC와 UIA 조회가 전경을 유지함")
        for index, o in enumerate(snapshots):
            e = next(e for e in o["elements"] if e["name"] == "PilotValue")
            cursor, _ = client.tool("cursor_update", {"cursor_id": f"cursor-{index}", "window_id": o["window"]["window_id"],
                    "observation_id": o["observation_id"], "x": 50 + index * 20, "y": 50, "element_id": e["element_id"]})
            assert cursor["kind"] == "logical_only"
        listing, _ = client.tool("windows_list")
        assert len(listing["cursors"]) == 2
        assert len({c["window_id"] for c in listing["cursors"]}) == 2
        checks.append("창별 논리 커서와 논리 포커스가 독립적으로 유지됨")
        assert pointer_position() == initial_pointer
        checks.append("논리 커서 변경 시 실제 시스템 커서 위치 유지")
        o = snapshots[0]
        edit = next(e for e in o["elements"] if e["name"] == "PilotValue")
        args = {"window_id": a["window_id"], "observation_id": o["observation_id"], "request_id": "set-A",
                "type": "set_value", "element_id": edit["element_id"], "value": "백그라운드 검증", "foreground_policy": "never"}
        job, _ = client.tool("action_run", args)
        repeated, _ = client.tool("action_run", args)
        assert repeated["job_id"] == job["job_id"] and repeated["reused"]
        result = client.wait(job["job_id"])
        assert result["status"] == "completed" and result["verified"], result
        assert u32.GetForegroundWindow() == foreground
        checks.append("표준 Edit 백그라운드 값 변경 및 UIA 읽기 검증, 전경 유지")
        checks.append("동일 request_id 중복 접수 방지")
        conflict, _ = client.tool("action_run", args | {"value": "다른 값"}, allow_error=True)
        assert conflict["status"] == "request_id_conflict"
        checks.append("request_id를 다른 내용에 재사용하면 거부")
        stale, _ = client.tool("action_run", args | {"request_id": "stale"}, allow_error=True)
        assert stale["status"] == "stale_observation"
        checks.append("소비된 관찰로 두 번째 변경 거부")
        blocked, _ = client.tool("action_run", {"window_id": a["window_id"], "observation_id": o["observation_id"],
                  "request_id": "blocked", "type": "click", "x": 50, "y": 50}, allow_error=True)
        assert blocked["status"] == "foreground_required"
        for kind in ("click", "drag"):
            blocked, _ = client.tool("action_run", {"window_id": a["window_id"], "observation_id": o["observation_id"],
                       "request_id": "blocked-" + kind, "type": kind, "foreground_policy": "never",
                       "x": 50, "y": 50, "to_x": 80, "to_y": 80}, allow_error=True)
            assert blocked["status"] == "foreground_required"
        assert pointer_position() == initial_pointer
        checks.append("never 정책의 실제 마우스 클릭·드래그 요청 거부 및 커서 위치 유지")
        o, _ = client.tool("window_observe", {"window_id": a["window_id"], "capture": False})
        assert next(e for e in o["elements"] if e["name"] == "PilotValue")["value"] == "백그라운드 검증"
        button = next(e for e in o["elements"] if e["name"] == "PilotButton")
        job, _ = client.tool("action_run", {"window_id": a["window_id"], "observation_id": o["observation_id"],
                "request_id": "invoke", "type": "invoke", "element_id": button["element_id"]})
        result = client.wait(job["job_id"])
        assert result["status"] in ("dispatched_unverified", "interference_detected") and not result["verified"], result
        o, _ = client.tool("window_observe", {"window_id": a["window_id"], "capture": False})
        assert any(e["name"] == "Count:1" or e.get("value") == "Count:1" for e in o["elements"]), o["elements"]
        checks.append("Invoke는 완료로 오인하지 않으며 전경 변경을 보고하고 별도 관찰로 클릭 결과 확인")
        # 자체 시험 앱의 버튼은 값을 변경한 뒤 입력란에 포커스를 준다. 마우스 입력은 하지 않는다.
        assert pointer_position() == initial_pointer
        u32.GetAsyncKeyState.restype = ctypes.c_short
        # 키 취소 검사는 입력란을 실제 클릭해 전경이 된 상태에서 시작한다.
        o, _ = client.tool("window_observe", {"window_id": a["window_id"]})
        edit = next(e for e in o["elements"] if e["name"] == "PilotValue")["bounds"]
        job, _ = client.tool("action_run", {"window_id": a["window_id"], "observation_id": o["observation_id"],
            "request_id": "prepare-key-focus", "type": "click", "foreground_policy": "allow",
            "x": edit["x"] - o["capture"]["bounds"]["x"] + 20,
            "y": edit["y"] - o["capture"]["bounds"]["y"] + 10})
        result = client.wait(job["job_id"])
        assert result["status"] == "dispatched_unverified", result
        assert u32.GetForegroundWindow() == a["hwnd"], result
        checks.append("관찰한 입력란 클릭 후 실제 전경 창 확인")
        cancellation_ms = {}
        for cancel_tool in ("job_cancel", "stop_all"):
            o, _ = client.tool("window_observe", {"window_id": a["window_id"]})
            job, _ = client.tool("action_run", {"window_id": a["window_id"], "observation_id": o["observation_id"],
                        "request_id": cancel_tool, "type": "key", "foreground_policy": "allow",
                        "key_target": "window", "virtual_key": 65, "duration_ms": 2000})
            deadline = time.monotonic() + 6
            while u32.GetAsyncKeyState(65) >= 0 and time.monotonic() < deadline:
                time.sleep(.005)
            assert u32.GetAsyncKeyState(65) < 0, ("키 누름을 관측하지 못했습니다.", client.tool("job_status", {"job_id": job["job_id"]})[0])
            started = time.monotonic()
            cancelled, _ = client.tool(cancel_tool, {"job_id": job["job_id"]} if cancel_tool == "job_cancel" else {})
            assert cancelled["cancellation_requested"] == 1
            result = client.wait(job["job_id"])
            cancellation_ms[cancel_tool] = round((time.monotonic() - started) * 1000, 1)
            assert result["status"] == "interrupted", result
            assert u32.GetAsyncKeyState(65) >= 0, "취소 후 키가 눌린 상태입니다."
            checks.append(cancel_tool + " 실행 중 키 입력 중단 및 실제 key-up 확인")
        closed_fixture = next(p for p in fixtures if p.pid == a["pid"])
        closed_fixture.terminate()
        closed_fixture.wait(timeout=5)
        gone, raw = client.tool("window_observe", {"window_id": a["window_id"]}, allow_error=True)
        assert raw["isError"]
        checks.append("닫힌 창을 이전 참조로 조작하지 않음")
        checks.append("allow 전경 활성화는 커서를 이동할 수 있으며 never 구간은 앞서 보존 검사함")
        return {"status": "passed", "checks": checks, "scope": "자체 WinForms fixture 2개",
                "cancellation_observed_ms": cancellation_ms, "game_input_tested": False,
                "foreground_activation_may_move_pointer": True, "pointer_before": initial_pointer, "pointer_after": pointer_position()}
    finally:
        if client:
            client.close()
        for p in fixtures:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", nargs="+")
    args = parser.parse_args()
    (ROOT / "artifacts").mkdir(exist_ok=True)
    result = inspect_targets(args.inspect) if args.inspect else integration()
    output = ROOT / "artifacts" / ("targets.json" if args.inspect else "integration.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
