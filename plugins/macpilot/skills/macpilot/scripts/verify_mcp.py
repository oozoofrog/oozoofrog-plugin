#!/usr/bin/python3
"""Development-only MCP stdio and cancellation regression harness."""

import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time


skill = Path(__file__).resolve().parent.parent
package = skill / "tool"


def check(condition, message, detail=None):
    if not condition:
        raise AssertionError(f"{message}: {detail!r}")


class MCPServer:
    def __init__(self, binary, state_directory):
        environment = os.environ.copy()
        environment["MACPILOT_STATE_DIR"] = str(state_directory)
        self.process = subprocess.Popen(
            [str(binary), "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=environment,
        )

    def send(self, message):
        self.send_line(json.dumps(message, ensure_ascii=False))

    def send_line(self, line):
        check(self.process.stdin is not None and not self.process.stdin.closed, "MCP stdin is closed")
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def read(self, timeout=2):
        check(self.process.stdout is not None, "MCP stdout is unavailable")
        readable, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not readable:
            return None
        line = self.process.stdout.readline()
        return json.loads(line) if line else None

    def close_stdin(self):
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()

    def wait(self, timeout=2):
        return self.process.wait(timeout=timeout)

    def stop(self):
        self.close_stdin()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


def initialize(server, request_id=1):
    server.send({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {"protocolVersion": "2025-11-25"},
    })
    response = server.read()
    check(response is not None and response.get("id") == request_id and "result" in response,
          "initialize did not respond while stdin remained open", response)


def tool_error_code(response):
    result = response.get("result", {})
    content = result.get("content", [])
    if not result.get("isError") or not content:
        return None
    return json.loads(content[0]["text"]).get("code")


subprocess.run(
    ["/usr/bin/xcrun", "swift", "build", "--package-path", str(package), "--product", "macpilot"],
    check=True,
)
binary_directory = Path(subprocess.check_output(
    ["/usr/bin/xcrun", "swift", "build", "--package-path", str(package), "--show-bin-path"],
    text=True,
).strip())
binary = binary_directory / "macpilot"

checks = []
with tempfile.TemporaryDirectory(prefix="macpilot-mcp-") as temporary:
    root = Path(temporary)
    state_directory = root / "state"

    server = MCPServer(binary, state_directory)
    try:
        initialize(server)
        checks.append("live initialize response before EOF")
        server.send_line("{invalid json")
        parse_error = server.read()
        check(parse_error is not None and parse_error.get("error", {}).get("code") == -32700,
              "parse error was not flushed while stdin remained open", parse_error)
        checks.append("live parse error response before EOF")
        server.close_stdin()
        check(server.wait() == 0, "MCP server failed after clean stdin EOF")
    finally:
        server.stop()

    server = MCPServer(binary, state_directory)
    try:
        initialize(server)
        delayed = {
            "jsonrpc": "2.0",
            "id": "active",
            "method": "tools/call",
            "params": {
                "name": "mac_script",
                "arguments": {
                    "language": "applescript",
                    "source": "delay 10\nreturn 1",
                    "timeoutMs": 60000,
                    "maxOutputBytes": 4096,
                },
            },
        }
        server.send(delayed)
        server.send({
            "jsonrpc": "2.0",
            "id": "other",
            "method": "tools/call",
            "params": {"name": "mac_doctor", "arguments": {}},
        })
        server.send(delayed)
        first = server.read()
        second = server.read()
        responses = {response.get("id"): response for response in (first, second) if response is not None}
        check(tool_error_code(responses.get("other", {})) == "busy",
              "a distinct concurrent tool call did not receive busy", responses)
        duplicate = responses.get("active", {})
        check(duplicate.get("error", {}).get("code") == -32600,
              "a duplicate active request id was not rejected", responses)
        checks.append("legacy state collision and duplicate id rejection")
        server.send({"jsonrpc":"2.0","id":"new-task","method":"tools/call","params":{"name":"mac_task","arguments":{"operation":"begin"}}})
        created=server.read()
        check(created is not None and created.get("id")=="new-task" and not created.get("result",{}).get("isError"),"parallel task creation failed",created)
        task_id=created["result"]["structuredContent"]["task"]["id"]
        server.send({"jsonrpc":"2.0","id":"independent","method":"tools/call","params":{"name":"mac_doctor","arguments":{"taskID":task_id}}})
        independent=server.read()
        check(independent is not None and independent.get("id")=="independent" and not independent.get("result",{}).get("isError"),"independent task did not execute while legacy work was active",independent)
        checks.append("independent MCP task executes while another request is active")

        server.send({
            "jsonrpc": "2.0",
            "method": "notifications/cancelled",
            "params": {"requestId": "active", "reason": "regression test"},
        })
        time.sleep(0.6)
        server.send({
            "jsonrpc": "2.0",
            "id": "after-cancel",
            "method": "tools/call",
            "params": {"name": "mac_doctor", "arguments": {}},
        })
        after = server.read()
        check(after is not None and after.get("id") == "after-cancel" and tool_error_code(after) != "busy",
              "cancelled call did not release the active slot or emitted a stale response", after)
        checks.append("cancel notification suppresses stale response and releases capacity")
        server.close_stdin()
        check(server.wait() == 0, "MCP server failed after cancelled request")
    finally:
        server.stop()

    started_marker = root / "started"
    finished_marker = root / "finished"
    source = (
        f'do shell script "/usr/bin/touch " & quoted form of "{started_marker}"\n'
        "delay 2\n"
        f'do shell script "/usr/bin/touch " & quoted form of "{finished_marker}"'
    )
    server = MCPServer(binary, state_directory)
    try:
        initialize(server)
        server.send({
            "jsonrpc": "2.0",
            "id": "eof-active",
            "method": "tools/call",
            "params": {
                "name": "mac_script",
                "arguments": {
                    "language": "applescript",
                    "source": source,
                    "timeoutMs": 60000,
                    "maxOutputBytes": 4096,
                },
            },
        })
        deadline = time.monotonic() + 2
        while not started_marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        check(started_marker.exists(), "EOF cancellation test script did not start")
        began = time.monotonic()
        server.close_stdin()
        check(server.wait(timeout=2) == 0, "MCP server did not exit after stdin EOF")
        check(time.monotonic() - began < 1.5, "MCP EOF cleanup exceeded its shutdown bound")
        time.sleep(2.1)
        check(not finished_marker.exists(), "active child process survived MCP stdin EOF")
        checks.append("bounded EOF cancellation terminates active child work")
    finally:
        server.stop()

print(json.dumps({"status": "passed", "checks": checks}, ensure_ascii=False, indent=2))
