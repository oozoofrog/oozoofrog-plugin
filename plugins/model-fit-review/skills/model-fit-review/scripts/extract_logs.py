#!/usr/bin/env python3
"""Extract human messages and Claude runs from Claude Code session logs.

Usage: extract_logs.py --out <dir> [--projects ~/.claude/projects]
       [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--t3-db <snapshot.sqlite>]

One session file is one thread. Every prompt starts a run: a human prompt
starts a human-initiated run, an injected prompt (delegation brief or result,
notification, relayed message, compact summary) starts an agent-initiated run
(mfrlib.prompt_kind). A run ends at the last assistant entry before the next
prompt. Subagent files and sidechain entries are skipped. Model comes from the
assistant entries; effort from an entry's `effort` field when present.

--since/--until are inclusive UTC dates applied to the run's first request
time. --t3-db makes the T3 DB the authority for sessions it knows (nativeThreadRef.nativeId
= session file name): there a log prompt is human only if it matches a T3
human message by time and normalized text; unmatched prompts become
agent-initiated. Sessions the DB does not know keep the log rules.

Logs have no separate completion event per message, so a message sent while
a turn was running cannot be told apart: log-only runs have no steer.
Writes <dir>/messages.jsonl and <dir>/runs.jsonl. Honors TMPDIR.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402


def session_files(projects: Path) -> list[Path]:
    return sorted(p for p in projects.glob("*/*.jsonl") if "subagents" not in p.parts)


BARE_COMMAND = re.compile(r"^/[\w:.-]+$")


def skill_text(entry: dict) -> str | None:
    """First text part of a meta entry, when it is the user's typed text and
    not the skill body ("Base directory for this skill: ...")."""
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        return None
    t = (content[0].get("text") or "").strip() if content[0].get("type") == "text" else ""
    if not t or t.startswith(("<", "Base directory")):
        return None
    return t


def parse_session(path: Path) -> tuple[list[dict], list[dict]]:
    """All prompts of one session. Returns (prompts, runs); each prompt has a
    `kind` ("human" or "agent"), each run an `initiator`."""
    thread = path.stem
    prompts, runs, cur = [], [], None

    def close():
        if cur and cur["_models"]:
            (model, _), = cur["_models"].most_common(1)
            efforts = cur["_efforts"].most_common(1)
            runs.append({"run_id": cur["run_id"], "thread": thread, "provider": "claude",
                         "initiator": cur["initiator"], "model": model,
                         "effort": efforts[0][0] if efforts else None,
                         "requested_at": cur["requested_at"], "completed_at": cur["completed_at"],
                         "request": cur["request"], "request_ids": [cur["msg_id"]] if cur["initiator"] == "human" else [],
                         "prompt_id": cur["msg_id"], "reply_end": cur["reply_end"][-700:],
                         "max_context_tokens": cur["max_ctx"], "source": "logs"})

    with open(path, encoding="utf-8", errors="replace") as f:
        for n, line in enumerate(f):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            ts = d.get("timestamp") or ""
            kind, text = mfrlib.prompt_kind(d)
            if kind is not None:
                close()
                mid = f"{thread}:{n}"
                prompts.append({"id": mid, "thread": thread, "at": ts, "text": text, "kind": kind,
                                "run_id": f"{thread}:run{len(prompts) + 1}", "provider": "claude"})
                cur = {"run_id": prompts[-1]["run_id"], "msg_id": mid, "requested_at": ts, "initiator": kind,
                       "completed_at": None, "request": text, "reply_end": "", "max_ctx": 0,
                       "_models": collections.Counter(), "_efforts": collections.Counter()}
            elif cur and d.get("isMeta") and not cur["_models"] and BARE_COMMAND.match(cur["request"]):
                typed = skill_text(d)
                if typed:  # a slash-invoked skill keeps the typed text in the meta entry after it
                    cur["request"] = prompts[-1]["text"] = typed
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
    return prompts, runs


def t3_authority(db_path: str) -> tuple[dict[str, str], list[dict]]:
    """({session id: T3 thread}, T3 human messages) from a snapshot."""
    import extract_t3  # local import: only needed with --t3-db
    db = extract_t3.open_snapshot(db_path)
    nmap = extract_t3.native_map(db)
    t3 = [{"id": i, "thread": t, "at": at, "text": text or ""}
          for i, t, at, text in db.execute("select id, thread, at, text from hmsg")]
    db.close()
    return nmap, t3


def apply_authority(prompts: list[dict], runs: list[dict], nmap: dict[str, str], t3: list[dict]) -> dict:
    """Demote log prompts in T3-known sessions that match no T3 human message."""
    known = [dict(p, thread=nmap[p["thread"]]) for p in prompts if p["thread"] in nmap]
    pairs = mfrlib.match_prompts([p for p in known if p["kind"] == "human"], t3)
    stats = collections.Counter()
    demoted = set()
    for p in prompts:
        if p["thread"] not in nmap:
            stats["unmapped " + p["kind"]] += 1
            continue
        if p["kind"] != "human":
            stats["mapped agent"] += 1
        elif p["id"] in pairs or mfrlib.is_control(p["text"]):  # T3 may not store session commands
            p["t3_message_id"] = pairs.get(p["id"])
            stats["mapped human, matched T3 (or a session command)"] += 1
        else:
            p["kind"] = "agent"
            demoted.add(p["id"])
            stats["mapped human, no T3 match -> agent"] += 1
    for r in runs:
        if r["prompt_id"] in demoted:
            r["initiator"], r["request_ids"] = "agent", []
    return dict(stats)


def extract(projects: Path, t3_db: str | None = None) -> tuple[list[dict], list[dict], dict]:
    """Returns (human messages, runs with reactions, authority stats), all time."""
    prompts, runs = [], []
    for p in session_files(projects):
        m, r = parse_session(p)
        prompts += m
        runs += r
    stats = {}
    if t3_db:
        stats = apply_authority(prompts, runs, *t3_authority(t3_db))
    messages = [{k: v for k, v in p.items() if k != "kind"} for p in prompts if p["kind"] == "human"]
    return messages, mfrlib.assign_reactions(runs, messages), stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projects", default=str(Path.home() / ".claude" / "projects"))
    ap.add_argument("--since", default="", help="inclusive UTC date YYYY-MM-DD")
    ap.add_argument("--until", default="", help="inclusive UTC date YYYY-MM-DD")
    ap.add_argument("--t3-db", help="T3 snapshot; its human messages decide which log prompts are human")
    ap.add_argument("--out", required=True)
    ap.add_argument("--allow-repo", action="store_true", help="allow --out inside a git work tree")
    ap.add_argument("--check-sample", type=int, default=10, help="random human messages to write for the precision check")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    out = Path(a.out)
    err = mfrlib.check_output_dir(out, a.allow_repo)
    if err:
        print(err, file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    messages, runs, stats = extract(Path(a.projects).expanduser(), a.t3_db)
    messages, runs = mfrlib.apply_window(messages, runs, a.since, a.until)
    mfrlib.write_jsonl(out / "messages.jsonl", messages)
    mfrlib.write_jsonl(out / "runs.jsonl", runs)
    path, k = mfrlib.write_check_sample(out, messages, a.since, a.until, a.check_sample, a.seed)
    print(f"precision check: read the {k} rows in {path.name}; record how many a person typed")
    for k, v in sorted(stats.items()):
        print(f"T3 authority (all time): {k} {v}")
    for line in mfrlib.summary(messages, runs, a.since, a.until):
        print(line)
    human = [r for r in runs if r["initiator"] == "human"]
    if sum(1 for r in human if r["effort"]) < len(human):
        print("note: effort is unknown for some runs; say so in the report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
