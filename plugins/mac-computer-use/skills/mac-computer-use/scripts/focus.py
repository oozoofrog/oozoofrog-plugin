#!/usr/bin/env python3
"""
focus.py: show which windows mac-cu works on (focus glow and preview, see focus-overlay.swift).

    focus.py post       PostToolUse hook for the mac-cu tools. Reads every target window named
                        in the tool result (`Window: "<title>", App: <app>.`) and starts one
                        focus-overlay for each window, or keeps the running one.
    focus.py stop       Stop hook: remove the overlays of this session when Claude's turn ends.
    focus.py subagent-stop
                        SubagentStop hook: remove the overlays of that subagent.
    focus.py selftest   Check the tool-result parser.

Each Claude Code session and each subagent has its own overlays and its own glow color, so several
sessions can work on different windows at the same time. A hook never blocks Claude Code: on any
problem it does nothing. Standard library only.
"""

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

OVERLAY = Path(__file__).resolve().parent / "focus-overlay"
STATES = Path(tempfile.gettempdir()) / "codex-cu-focus"
# `mac-cu --mode show=off` turns the glow off (Modes.swift).
MODES = Path.home() / "Library/Application Support/mac-cu/modes.json"
# A full state starts with `Window: "<title>", App: <app>.`; a diff names only the window.
TARGET = re.compile(
    r'Window: "(?P<title>.*?)"(?:, App: (?P<app>.+?)\.$|\.$| with ~)', re.MULTILINE)
# Glow colors, one for each session or subagent.
COLORS = ["339cff", "34c759", "ff9f0a", "bf5af2", "ff375f", "64d2ff"]


def texts(value):
    """Yield every string in the tool result (its shape differs between versions)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from texts(item)
    elif isinstance(value, list):
        for item in value:
            yield from texts(item)


def targets(response) -> list:
    """Return the distinct (title, app or None) windows named in the result, in order."""
    found = []
    for text in texts(response):
        for match in TARGET.finditer(text):
            target = (match["title"], match["app"])
            if target not in found:
                found.append(target)
    return found


def safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", text or "unknown")


def owner_prefix(session_id: str, agent_id: str = "") -> str:
    """State files of one session start with the session; those of a subagent also name the agent."""
    return f"{safe(session_id)}__{safe(agent_id or 'main')}__"


def state_file(prefix: str, title: str) -> Path:
    return STATES / (prefix + hashlib.sha1(title.encode()).hexdigest()[:10] + ".json")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def is_overlay(pid) -> bool:
    if not isinstance(pid, int):
        return False
    ps = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True)
    return ps.stdout.strip().endswith("focus-overlay")


def stop_overlays(prefix: str) -> None:
    for path in STATES.glob(prefix + "*.json") if STATES.is_dir() else []:
        pid = load(path).get("pid")
        if is_overlay(pid):
            os.kill(pid, signal.SIGTERM)
        path.unlink(missing_ok=True)


def start_overlay(path: Path, title: str, app, color: str) -> None:
    STATES.mkdir(parents=True, exist_ok=True)
    state = {"app": app, "title": title}
    path.write_text(json.dumps(state))  # Must exist before the overlay starts.
    command = [str(OVERLAY), "--title", title, "--color", color, "--state", str(path)]
    if app:
        command += ["--owner", app]
    overlay = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    path.write_text(json.dumps({**state, "pid": overlay.pid}))


def on_post(event: dict) -> None:
    if not OVERLAY.exists():
        return
    prefix = owner_prefix(event.get("session_id", ""), event.get("agent_id", ""))
    if load(MODES).get("show") == "off":
        stop_overlays(prefix)
        return
    color = COLORS[int(hashlib.sha1(prefix.encode()).hexdigest(), 16) % len(COLORS)]
    for title, app in targets(event.get("tool_response")):
        path = state_file(prefix, title)
        state = load(path)
        if is_overlay(state.get("pid")) and (app is None or state.get("app") in (app, None)):
            path.touch()  # The overlay stops by itself when this file gets old.
            continue
        if is_overlay(state.get("pid")):
            os.kill(state["pid"], signal.SIGTERM)
        start_overlay(path, title, app or state.get("app"), color)


def selftest() -> None:
    assert targets([{"type": "text", "text": 'docs\nWindow: "계산기", App: 계산기.\n0 window'}]) == [("계산기", "계산기")]
    assert targets('There has been no change in the accessibility tree for Window: "A "q" b".') == [('A "q" b', None)]
    assert targets({"c": ['Window: "One", App: X.', 'Window: "Two", App: Y Z.', 'Window: "One", App: X.']}) == [("One", "X"), ("Two", "Y Z")]
    assert targets('The following is a diff from the previous accessibility tree for Window: "계산기" with ~ and +') == [("계산기", None)]
    assert targets("nothing here") == []
    assert owner_prefix("s-1", "") == "s-1__main__" and owner_prefix("s-1", "a/2") == "s-1__a_2__"
    print("ok")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "selftest":
        selftest()
        return 0
    try:
        event = json.load(sys.stdin)
        if mode == "post":
            on_post(event)
        elif mode == "stop":
            stop_overlays(safe(event.get("session_id", "")) + "__")
        elif mode == "subagent-stop":
            stop_overlays(owner_prefix(event.get("session_id", ""), event.get("agent_id", "")))
    except Exception:
        pass  # A missing glow must never interrupt Claude Code.
    return 0


if __name__ == "__main__":
    sys.exit(main())
