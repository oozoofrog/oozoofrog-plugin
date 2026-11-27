#!/usr/bin/env python3
"""Extract human messages and Claude runs from a T3 Code state DB snapshot.

Usage: extract_t3.py --db <snapshot.sqlite> --out <dir>
Writes <dir>/messages.jsonl and <dir>/runs.jsonl (see mfrlib for the shapes).
The snapshot is opened read-only; helper tables are TEMP tables.
Make the snapshot first with snapshot_db.py; never point this at the live DB.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402


def extract(db_path: str) -> tuple[list[dict], list[dict]]:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.executescript((Path(__file__).resolve().parent / "build_tables.sql").read_text(encoding="utf-8"))
    messages = [{"id": i, "thread": t, "at": at, "text": text or ""}
                for i, t, at, text in db.execute("select id, thread, at, text from hmsg order by thread, at, id")]
    rows = db.execute("""select run_id, thread, model, effort, completed_at, msg_id, msg_at, msg_text, reply_end
                         from hruns order by thread, msg_at, run_id""").fetchall()
    runs = []
    for run_id, thread, model, effort, done, mid, mat, mtext, reply in rows:
        runs.append({"run_id": run_id, "thread": thread, "model": model, "effort": effort,
                     "requested_at": mat, "completed_at": done, "request": mtext or "",
                     "request_ids": [mid], "reply_end": (reply or "")[-700:],
                     "max_context_tokens": None, "source": "t3"})
    db.close()
    return messages, mfrlib.assign_reactions(runs, messages)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    messages, runs = extract(a.db)
    mfrlib.write_jsonl(out / "messages.jsonl", messages)
    mfrlib.write_jsonl(out / "runs.jsonl", runs)
    steer = sum(len(r["steer_ids"]) for r in runs)
    print(f"human messages {len(messages)}  distinct runs {len(runs)}  steer messages {steer}  "
          f"effort known {sum(1 for r in runs if r['effort'])}/{len(runs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
