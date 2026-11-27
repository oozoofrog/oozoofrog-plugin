#!/usr/bin/env python3
"""Extract human messages and Claude runs from Claude Code session logs.

Usage: extract_logs.py --out <dir> [--projects ~/.claude/projects] [--since 2026-01-01]

One session file is one thread. A run starts at a human message and ends at
the last assistant entry before the next human message. Subagent files and
sidechain entries are skipped. Model comes from the assistant entries; effort
comes from an entry's `effort` field when the log has one, otherwise it is
unknown. Logs have no separate completion event, so a message sent while a
turn was running cannot be told apart: log-only runs have no steer messages.
Writes <dir>/messages.jsonl and <dir>/runs.jsonl.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402


def session_files(projects: Path) -> list[Path]:
    return sorted(p for p in projects.glob("*/*.jsonl") if "subagents" not in p.parts)


def parse_session(path: Path, since: str = "") -> tuple[list[dict], list[dict]]:
    thread = path.stem
    messages, runs, cur = [], [], None

    def close():
        if cur and cur["_models"]:
            (model, _), = cur["_models"].most_common(1)
            efforts = cur["_efforts"].most_common(1)
            runs.append({"run_id": cur["run_id"], "thread": thread, "model": model,
                         "effort": efforts[0][0] if efforts else None,
                         "requested_at": cur["requested_at"], "completed_at": cur["completed_at"],
                         "request": cur["request"], "request_ids": [cur["msg_id"]],
                         "reply_end": cur["reply_end"][-700:],
                         "max_context_tokens": cur["max_ctx"], "source": "logs"})

    with open(path, encoding="utf-8", errors="replace") as f:
        for n, line in enumerate(f):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            ts = d.get("timestamp") or ""
            text = mfrlib.log_human_text(d)
            if text is not None:
                close()
                cur = None
                if ts < since:
                    continue
                mid = f"{thread}:{n}"
                messages.append({"id": mid, "thread": thread, "at": ts, "text": text})
                cur = {"run_id": f"{thread}:run{len(messages)}", "msg_id": mid, "requested_at": ts,
                       "completed_at": None, "request": text, "reply_end": "", "max_ctx": 0,
                       "_models": collections.Counter(), "_efforts": collections.Counter()}
            elif cur and d.get("type") == "assistant" and not d.get("isSidechain"):
                m = d.get("message") or {}
                model = m.get("model")
                if not model or model.startswith("<"):
                    continue
                cur["_models"][model] += 1
                if d.get("effort"):
                    cur["_efforts"][str(d["effort"])] += 1
                cur["completed_at"] = ts or cur["completed_at"]
                u = m.get("usage") or {}
                ctx = sum(int(u.get(k) or 0) for k in
                          ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
                cur["max_ctx"] = max(cur["max_ctx"], ctx)
                t = "\n".join(x.get("text", "") for x in m.get("content") or []
                              if isinstance(x, dict) and x.get("type") == "text").strip()
                if t:
                    cur["reply_end"] = t
    close()
    return messages, runs


def extract(projects: Path, since: str = "") -> tuple[list[dict], list[dict]]:
    messages, runs = [], []
    for p in session_files(projects):
        m, r = parse_session(p, since)
        messages += m
        runs += r
    return messages, mfrlib.assign_reactions(runs, messages)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projects", default=str(Path.home() / ".claude" / "projects"))
    ap.add_argument("--since", default="", help="ISO date; skip human messages before it")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    messages, runs = extract(Path(a.projects).expanduser(), a.since)
    mfrlib.write_jsonl(out / "messages.jsonl", messages)
    mfrlib.write_jsonl(out / "runs.jsonl", runs)
    known = sum(1 for r in runs if r["effort"])
    print(f"human messages {len(messages)}  runs {len(runs)}  effort known {known}/{len(runs)}")
    if known < len(runs):
        print("note: effort is unknown for some runs; say so in the report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
