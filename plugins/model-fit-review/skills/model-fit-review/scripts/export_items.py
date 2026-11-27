#!/usr/bin/env python3
"""Export classifier items for follow-up labels, without model names.

Usage: export_items.py --data <dir> [--calib 40] [--seed 7]
Reads <dir>/messages.jsonl and <dir>/runs.jsonl. Writes:
- items.jsonl: {id, request, assistant_reply_end, next_user_message}, shuffled
- calib.jsonl: the first --calib items, for hand labels before any classifier
- key.json: item id -> {message_id, run_id, kind}; the key holds no text and
  stays with the main agent, never with a classifier.
One item per reaction or steer message. Session-command reactions are left out.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402


def cut(s: str | None, n: int, tail: bool = False) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return ("…" + s[-n:]) if tail else (s[:n] + "…")


def build(messages: list[dict], runs: list[dict], seed: int = 7) -> tuple[list[dict], dict]:
    text = {m["id"]: m["text"] for m in messages}
    pairs = []
    for r in runs:
        if mfrlib.is_control(r["request"]):
            continue
        if r.get("reaction_id") and not mfrlib.is_control(text.get(r["reaction_id"])):
            pairs.append((r, r["reaction_id"], "reaction"))
        pairs += [(r, s, "steer") for s in r.get("steer_ids", [])]
    rng = random.Random(seed)
    rng.shuffle(pairs)
    items, key = [], {}
    for i, (r, mid, kind) in enumerate(pairs):
        iid = f"i{i:05d}"
        items.append({"id": iid, "request": cut(r["request"], 400),
                      "assistant_reply_end": cut(r.get("reply_end"), 700, tail=True),
                      "next_user_message": cut(text.get(mid), 400)})
        key[iid] = {"message_id": mid, "run_id": r["run_id"], "kind": kind}
    return items, key


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--calib", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    d = Path(a.data)
    items, key = build(mfrlib.read_jsonl(d / "messages.jsonl"), mfrlib.read_jsonl(d / "runs.jsonl"), a.seed)
    mfrlib.write_jsonl(d / "items.jsonl", items)
    mfrlib.write_jsonl(d / "calib.jsonl", items[:a.calib])
    (d / "key.json").write_text(json.dumps(key), encoding="utf-8")
    print(f"{len(items)} items; {min(a.calib, len(items))} in calib.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
