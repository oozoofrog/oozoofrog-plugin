#!/usr/bin/env python3
"""Development-only MCP connection diagnostics regression; no GUI or host restart."""

import argparse
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time


class Server:
    def __init__(self, binary, state):
        self.process = subprocess.Popen([str(binary), "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, bufsize=0,
                                        env=dict(os.environ, MACPILOT_STATE_DIR=str(state)))
        self.buffer = b""
        self.sequence = 0
        self.request("initialize", {"protocolVersion": "2025-11-25"})

    def request(self, method, params):
        self.sequence += 1
        message = {"jsonrpc": "2.0", "id": self.sequence, "method": method, "params": params}
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if b"\n" in self.buffer:
                line, self.buffer = self.buffer.split(b"\n", 1)
                result = json.loads(line)
                if result.get("id") == self.sequence:
                    assert "error" not in result, result
                    return result["result"]
                continue
            assert select.select([self.process.stdout], [], [], max(0, deadline - time.monotonic()))[0], method
            chunk = os.read(self.process.stdout.fileno(), 65536)
            assert chunk, (method, "unexpected EOF")
            self.buffer += chunk
            assert len(self.buffer) <= 2_000_000
        raise TimeoutError(method)

    def call(self, name, **arguments):
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        assert not result.get("isError"), result
        return result["structuredContent"]

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=2)
        self.process.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    skill = Path(__file__).resolve().parent.parent
    output = skill / "evidence" / "connection-current"
    output.mkdir(parents=True, exist_ok=True)
    checks, evidence = [], {}

    def check(name, condition):
        assert condition, name
        checks.append(name)

    def cli(*arguments, state):
        result = subprocess.run([str(binary), *arguments], capture_output=True, text=True, timeout=15,
                                env=dict(os.environ, MACPILOT_STATE_DIR=str(state)))
        assert result.returncode == 0, (result.stdout, result.stderr)
        return json.loads(result.stdout)

    with tempfile.TemporaryDirectory(prefix="macpilot-connection-verify-") as directory:
        root = Path(directory)
        first, second = Server(binary, root / "first"), Server(binary, root / "second")
        try:
            a = first.call("mac_connection", operation="status")
            b = second.call("mac_connection", operation="status")
            evidence.update(first=a, second=b)
            check("MCP status identifies its exact child PID", a["server"]["pid"] == first.process.pid)
            check("two MCP connections have distinct instance IDs", a["server"]["instanceID"] != b["server"]["instanceID"])
            check("host call has MCP transport scope", a["transport"] == "mcp_stdio" and a["hostConnectionVerified"])
            check("parent identifies this harness, not an assumed Codex process", a["parent"]["pid"] == os.getpid())
            catalog = first.request("tools/list", {})["tools"]
            check("fresh MCP exposes condition/trace/image/workflow APIs",
                  {"mac_wait_for", "mac_trace", "mac_image_search", "mac_workflow"}.issubset({item["name"] for item in catalog}))
            task_schema = next(item for item in catalog if item["name"] == "mac_task")["inputSchema"]
            check("fresh MCP exposes explicit interrupted-task resume", "resume" in task_schema["properties"]["operation"]["enum"])
            tool = next(item for item in catalog if item["name"] == "mac_connection")
            check("diagnostics schema exposes only read-only operations", tool["annotations"]["readOnlyHint"] and
                  tool["inputSchema"]["properties"]["operation"]["enum"] == ["status", "probe"] and
                  "taskID" not in tool["inputSchema"]["properties"])
            baseline = dict(previousServerPID=a["server"]["pid"], previousServerStartID=a["server"]["processStartID"],
                            previousParentPID=a["parent"]["pid"], previousParentStartID=a["parent"]["processStartID"])
            repeat = first.call("mac_connection", operation="status", **baseline)
            check("same connection compares server and parent identities", repeat["server"]["comparison"]["relation"] == "same_instance" and
                  repeat["parent"]["comparison"]["relation"] == "same_instance")
            probe = first.call("mac_connection", operation="probe", **baseline)
            evidence["mcpProbe"] = probe
            check("isolated MCP probe passes real handshake and read-only calls", probe["status"] == "probe_passed" and probe["toolCount"] == len(catalog))
            check("probe does not claim caller reconnection", probe["scope"] == "isolated_probe" and not probe["hostConnectionVerified"])
            check("probe keeps caller identity distinct", probe["caller"]["server"]["instanceID"] == a["server"]["instanceID"] and
                  probe["probeConnection"]["server"]["instanceID"] != a["server"]["instanceID"])
            check("probe cleans only its owned child and state", probe["cleanup"]["childExited"] and probe["cleanup"]["temporaryStateRemoved"] and
                  probe["existingServersSignalled"] == 0 and not probe["globalReloadPerformed"])
            after_a = first.call("mac_connection", operation="status")
            after_b = second.call("mac_connection", operation="status")
            check("caller MCP stays alive after probe", after_a["server"] == a["server"])
            check("unrelated MCP stays alive after probe", after_b["server"] == b["server"])
            result = subprocess.run([str(binary), "call", "mac_connection", "--json", "-"], input=json.dumps(dict(operation="status", **baseline)),
                                    capture_output=True, text=True, timeout=5, env=dict(os.environ, MACPILOT_STATE_DIR=str(root / "cli")))
            assert result.returncode == 0, result.stdout
            one_shot = json.loads(result.stdout)
            evidence["cliStatus"] = one_shot
            check("CLI success is separate from host connection", one_shot["transport"] == "cli" and not one_shot["hostConnectionVerified"])
            check("CLI baseline recognizes live previous server", one_shot["server"]["comparison"]["relation"] == "different_instance" and
                  one_shot["server"]["comparison"]["previousInstanceRunning"])
            # An unusable existing state path must not prevent the fallback probe.
            unusable = root / "not-a-state-directory"
            unusable.write_text("owned sentinel")
            fallback = cli("connection-check", state=unusable)
            evidence["cliProbe"] = fallback
            check("CLI fallback bypasses the shared state and never claims host recovery", fallback["status"] == "probe_passed" and
                  not fallback["hostConnectionVerified"] and fallback["caller"]["transport"] == "cli")
            check("fallback preserves unusable original state", unusable.read_text() == "owned sentinel")
            check("unrelated connection remains usable after CLI fallback", second.call("mac_doctor")["status"] == "ok")
        finally:
            first.close()
            second.close()
    report = dict(status="passed", binary=str(binary), checks=checks, evidence=evidence,
                  limitations=["Owned MCP sessions only. Existing Desktop reconnection, TCC approval, GUI input and capture are separate evidence."])
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(status="passed", checkCount=len(checks), report=str(output / "report.json"))))


if __name__ == "__main__":
    main()
