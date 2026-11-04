#!/usr/bin/python3
"""Development-only MCP stdio and cancellation regression harness."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time
import traceback

from control_handoff_fixture import OwnedHandoffFixture, read_state


skill = Path(__file__).resolve().parent.parent
package = skill / "tool"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--binary', type=Path, help='Fresh signed MacPilot executable; otherwise builds debug with its own permission requirements')
parser.add_argument('--evidence', type=Path)
options = parser.parse_args()
evidence = options.evidence.resolve() if options.evidence else skill/'evidence'/('mcp-'+time.strftime('%Y%m%dT%H%M%S'))
evidence.mkdir(parents=True, exist_ok=False)


def check(condition, message, detail=None):
    if not condition:
        raise AssertionError(f"{message}: {detail!r}")


class MCPServer:
    def __init__(self, binary, state_directory):
        environment = os.environ.copy()
        environment["MACPILOT_STATE_DIR"] = str(state_directory)
        self._read_buffer = b""
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
        deadline = time.monotonic() + timeout
        descriptor = self.process.stdout.fileno()
        while True:
            if b"\n" in self._read_buffer:
                line, self._read_buffer = self._read_buffer.split(b"\n", 1)
                return json.loads(line)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            readable, _, _ = select.select([descriptor], [], [], remaining)
            if not readable:
                return None
            chunk = os.read(descriptor, 65536)
            if not chunk:
                return None
            self._read_buffer += chunk

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
    failure = json.loads(content[0]["text"])
    disposition = failure.get("disposition", {})
    expected_retry = {"not_delivered":"safe", "unknown":"unknown", "delivery_uncertain":"unsafe",
                      "delivered_unverified":"unsafe", "delivered_verified":"unsafe"}
    check(disposition.get("delivery") in expected_retry
          and disposition.get("retry") == expected_retry.get(disposition.get("delivery")),
          "tool error lost its delivery/retry contract", failure)
    check(result.get("structuredContent") == failure, "MCP text and structured error differ", result)
    return failure.get("code")


if options.binary:
    binary = options.binary.resolve()
else:
    built = subprocess.run(
        ["/usr/bin/xcrun", "swift", "build", "--package-path", str(package), "--product", "macpilot"],
        capture_output=True, text=True)
    (evidence/'build.log').write_text(built.stdout + built.stderr)
    built.check_returncode()
    binary_directory = Path(subprocess.check_output(
        ["/usr/bin/xcrun", "swift", "build", "--package-path", str(package), "--show-bin-path"], text=True).strip())
    binary = binary_directory / "macpilot"

fixture = OwnedHandoffFixture(evidence)

def foreground_task(server, request_id, goal, state_directory):
    server.send({'jsonrpc': '2.0', 'id': request_id, 'method': 'tools/call', 'params': {
        'name': 'mac_task', 'arguments': {'operation': 'begin', 'goal': goal,
            'preserveForeground': False, 'durationSeconds': 90}}})
    task_id = fixture.start(state_directory, server.process.pid, goal)
    result = server.read(timeout=5)
    check(result is not None and result.get('id') == request_id and not result.get('result', {}).get('isError'),
          'Owned foreground handoff did not finish', result)
    check(result['result']['structuredContent']['task']['id'] == task_id,
          'Handoff receipt changed task identity', result)
    return task_id


def finish_task(task_id, state_directory):
    environment = dict(os.environ, MACPILOT_STATE_DIR=str(state_directory))
    result = subprocess.run([str(binary), 'call', 'mac_task', '--json', '-'],
        input=json.dumps({'operation': 'finish', 'taskID': task_id}),
        capture_output=True, text=True, timeout=10, env=environment)
    check(result.returncode == 0, 'Owned foreground task cleanup failed', result.stdout + result.stderr)

checks = []
suite_error = None
completed = False
try:
    root = Path(tempfile.mkdtemp(prefix="macpilot-mcp-"))
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
        foreground_id = foreground_task(server, "foreground", "Owned MCP concurrency and cancellation fixture", state_directory)
        delayed = {
            "jsonrpc": "2.0",
            "id": "active",
            "method": "tools/call",
            "params": {
                "name": "mac_script",
                "arguments": {
                    "taskID": foreground_id,
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
            "params": {"name": "mac_doctor", "arguments": {"taskID": foreground_id}},
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
        checks.append("same-task state collision and duplicate id rejection under owned explicit handoff")
        server.send({"jsonrpc":"2.0","id":"new-task","method":"tools/call","params":{"name":"mac_task","arguments":{"operation":"begin"}}})
        created=server.read()
        check(created is not None and created.get("id")=="new-task" and not created.get("result",{}).get("isError"),"parallel task creation failed",created)
        task_id=created["result"]["structuredContent"]["task"]["id"]
        server.send({"jsonrpc":"2.0","id":"independent","method":"tools/call","params":{"name":"mac_doctor","arguments":{"taskID":task_id}}})
        independent=server.read()
        check(independent is not None and independent.get("id")=="independent" and not independent.get("result",{}).get("isError"),"independent task did not execute while foreground work was active",independent)
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
            "params": {"name": "mac_doctor", "arguments": {"taskID": foreground_id}},
        })
        after = server.read()
        check(after is not None and after.get("id") == "after-cancel" and tool_error_code(after) != "busy",
              "cancelled call did not release the active slot or emitted a stale response", after)
        checks.append("cancel notification suppresses stale response and releases capacity")
        finish_task(foreground_id, state_directory)
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
        eof_task_id = foreground_task(server, "eof-foreground", "Owned MCP EOF child cancellation fixture", state_directory)
        server.send({
            "jsonrpc": "2.0",
            "id": "eof-active",
            "method": "tools/call",
            "params": {
                "name": "mac_script",
                "arguments": {
                    "taskID": eof_task_id,
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
        finish_task(eof_task_id, state_directory)
    finally:
        server.stop()
    completed = True
except BaseException as error:
    suite_error = repr(error)
    (evidence/'failure.log').write_text(traceback.format_exc())
finally:
    # Host identity and exit are checked while its controller state still
    # exists. Failed suites retain the isolated state for investigation.
    cleanup_errors = fixture.stop_hosts()
    if completed and suite_error is None and not cleanup_errors:
        try:
            shutil.rmtree(root)
        except BaseException as error:
            cleanup_errors.append({'operation': 'remove owned temporary state', 'error': repr(error)})

report = {"status": "passed" if completed and suite_error is None and not cleanup_errors else "failed",
          "completed": completed and not cleanup_errors, "isolatedState": str(root),
          "stateRetained": root.exists(), "bodyFailure": suite_error, "cleanupFailures": cleanup_errors, "checks": checks,
          "binary": str(binary), "binarySHA256": hashlib.sha256(binary.read_bytes()).hexdigest(),
          "handoffAcceptance": "owned fixture AX automation, not human consent"}
(evidence/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False, indent=2))

if report["status"] != "passed":
    raise SystemExit(1)
