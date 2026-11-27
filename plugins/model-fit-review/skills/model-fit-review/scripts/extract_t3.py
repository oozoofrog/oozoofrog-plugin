#!/usr/bin/env python3
"""Extract human messages and Claude runs from a T3 Code state DB snapshot.

Usage: extract_t3.py --db <snapshot.sqlite> --out <dir> [--since YYYY-MM-DD]
       [--until YYYY-MM-DD] [--projects ~/.claude/projects] [--tmp DIR]

Writes <dir>/messages.jsonl and <dir>/runs.jsonl (see mfrlib for the shapes).
runs.jsonl holds every completed Claude run, human- or agent-initiated.
Reactions are assigned on the timeline of all completed runs of each thread,
any provider (mfrlib.assign_reactions).

--since/--until are inclusive UTC dates applied to the run's first request
time; reactions after --until still resolve. --projects adds per-run
max_context_tokens from the Claude Code logs, joined by
nativeThreadRef.nativeId = session file name and matched by time and
normalized text. --tmp sets SQLITE_TMPDIR for SQLite temporary tables
(otherwise SQLITE_TMPDIR or TMPDIR is used).

The snapshot is opened read-only and immutable; helper tables are TEMP tables.
Make the snapshot first with snapshot_db.py; never point this at the live DB.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402

HUMAN_FIRST = ("user|web", "user|mobile")


def open_snapshot(db_path: str) -> sqlite3.Connection:
    db = sqlite3.connect(mfrlib.ro_uri(db_path, immutable=True), uri=True)
    db.executescript((Path(__file__).resolve().parent / "build_tables.sql").read_text(encoding="utf-8"))
    return db


def native_map(db: sqlite3.Connection) -> dict[str, str]:
    """{Claude Code session id (log file stem): T3 thread id}."""
    return dict(db.execute("select native_id, thread from native"))


def extract(db_path: str) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    """Returns (messages, Claude runs, timeline, answer times), all time."""
    db = open_snapshot(db_path)
    messages = [{"id": i, "thread": t, "at": at, "text": text or "", "run_id": run, "provider": prov}
                for i, t, run, at, text, prov in
                db.execute("select id, thread, run_id, at, text, provider from hmsg order by thread, at, id")]
    by_run: dict[str, list[dict]] = {}
    for m in messages:
        if m["run_id"]:
            by_run.setdefault(m["run_id"], []).append(m)
    timeline, runs = [], []
    for run_id, thread, prov, req, done, model, effort, first_user, first_text, reply in db.execute(
            """select run_id, thread, provider, requested_at, completed_at, model, effort,
                      first_user, first_text, reply_end from truns order by thread, completed_at, run_id"""):
        timeline.append({"run_id": run_id, "thread": thread, "provider": prov, "completed_at": done})
        if not mfrlib.is_claude_provider(prov):
            continue
        attached = by_run.get(run_id, [])
        human = first_user in HUMAN_FIRST and bool(attached)
        runs.append({"run_id": run_id, "thread": thread, "provider": prov,
                     "initiator": "human" if human else "agent", "model": model, "effort": effort,
                     "requested_at": attached[0]["at"] if human else req, "completed_at": done,
                     "request": attached[0]["text"] if human else (first_text or ""),
                     "request_ids": [m["id"] for m in attached] if human else [],
                     "reply_end": (reply or "")[-700:], "max_context_tokens": None, "source": "t3"})
    answers = [at for (at,) in db.execute("select at from answers")]
    db.close()
    runs.sort(key=lambda r: (r["thread"], r["requested_at"], r["run_id"]))
    return messages, mfrlib.assign_reactions(runs, messages, timeline), timeline, answers


def add_log_context(db_path: str, runs: list[dict], projects: Path) -> tuple[int, int]:
    """Fill max_context_tokens and log_run_id on human-initiated runs from the
    matching log runs. Returns (matched, human-initiated runs)."""
    import extract_logs  # local import: only needed with --projects
    db = open_snapshot(db_path)
    nmap = native_map(db)
    db.close()
    log_msgs, log_runs = [], []
    for p in extract_logs.session_files(projects):
        if p.stem not in nmap:
            continue
        m, r = extract_logs.parse_session(p)
        for x in m:
            x["thread"] = nmap[p.stem]
        log_msgs += [x for x in m if x["kind"] == "human"]
        log_runs += r
    t3_msgs = [{"id": rid, "thread": r["thread"], "at": r["requested_at"], "text": r["request"]}
               for r in runs if r["initiator"] == "human" for rid in r["request_ids"][:1]]
    pairs = mfrlib.match_prompts(log_msgs, t3_msgs)
    by_log_msg = {r["request_ids"][0]: r for r in log_runs if r["request_ids"]}
    t3_to_log = {t3: by_log_msg.get(lg) for lg, t3 in pairs.items()}
    n = 0
    for r in runs:
        lr = t3_to_log.get((r["request_ids"] or [None])[0])
        if lr:
            r["max_context_tokens"], r["log_run_id"] = lr["max_context_tokens"], lr["run_id"]
            n += 1
    return n, sum(1 for r in runs if r["initiator"] == "human")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--since", default="", help="inclusive UTC date YYYY-MM-DD")
    ap.add_argument("--until", default="", help="inclusive UTC date YYYY-MM-DD")
    ap.add_argument("--projects", help="Claude Code projects dir, to add max_context_tokens")
    ap.add_argument("--tmp", help="directory for SQLite temporary files")
    ap.add_argument("--allow-repo", action="store_true", help="allow --out inside a git work tree")
    ap.add_argument("--check-sample", type=int, default=10, help="random human messages to write for the precision check")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    if a.tmp:
        os.environ["SQLITE_TMPDIR"] = a.tmp
    out = Path(a.out)
    err = mfrlib.check_output_dir(out, a.allow_repo)
    if err:
        print(err, file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    messages, runs, _, answers = extract(a.db)
    if a.projects:
        n, h = add_log_context(a.db, runs, Path(a.projects).expanduser())
        print(f"log join: {n}/{h} human-initiated runs matched a log run (all time)")
    messages, runs = mfrlib.apply_window(messages, runs, a.since, a.until)
    mfrlib.write_jsonl(out / "messages.jsonl", messages)
    mfrlib.write_jsonl(out / "runs.jsonl", runs)
    path, k = mfrlib.write_check_sample(out, messages, a.since, a.until, a.check_sample, a.seed)
    print(f"precision check: read the {k} rows in {path.name}; record how many a person typed")
    n_answers = sum(1 for at in answers if mfrlib.in_window(at, a.since, a.until)) if (a.since or a.until) else len(answers)
    for line in mfrlib.summary(messages, runs, a.since, a.until, answers=n_answers):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
