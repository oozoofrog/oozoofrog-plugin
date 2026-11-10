"""Claude Code hook entry point. Usage: ctx_hook.py session-start|stop|pre-compact|post-compact

Always exits 0: a hook failure must never block the user's prompt or session.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        inp = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    import ctxlib

    if event == "session-start":
        msg = ctxlib.session_start(inp)
        if msg:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                     "additionalContext": msg}}, ensure_ascii=False))
    elif event == "stop":
        out = ctxlib.stop(inp)
        if out:
            print(json.dumps(out, ensure_ascii=False))
    elif event == "pre-compact":
        msg = ctxlib.pre_compact(inp)
        if msg:
            print(msg)
    elif event == "post-compact":
        ctxlib.post_compact(inp)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — never propagate a hook failure
        print(f"handoff hook error: {e!r}", file=sys.stderr)
    sys.exit(0)
