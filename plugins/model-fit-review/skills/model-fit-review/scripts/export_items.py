#!/usr/bin/env python3
"""Export classifier items, without model names.

Usage: export_items.py --data <dir> [--calib 40] [--seed 7]
       export_items.py --data <dir> --episodes [--calib 30] [--seed 7]

Follow-up items (default). Reads <dir>/messages.jsonl and <dir>/runs.jsonl.
Writes:
- items.jsonl: {id, kind, request, assistant_reply_end, next_user_message},
  shuffled. kind is "reaction" (the message reacts to the run's result) or
  "steer" (sent while the run was going; assistant_reply_end is empty because
  the user had not seen it). Use the follow-up rubric for reactions and the
  steer rubric for steer (rubrics.md).
- calib.jsonl: a random sample of --calib REACTION items (fixed --seed), for
  hand labels before any classifier. Agreement is reported on reactions only.
- key.json: item id -> {message_id, run_id, kind}; the key holds no text and
  stays with the main agent, never with a classifier.
One item per reaction or steer message (mfrlib.reaction_items).

Task-type items (--episodes). Reads <dir>/episodes.jsonl and runs.jsonl.
Writes episode_items.jsonl ({id, source, requests: the first 6 human requests
cut at 220 characters, n_requests}), episode_calib.jsonl and episode_key.json
(item id -> episode). An episode with no human request (a delegated child
session) uses its agent-initiated requests (briefs) and has source "delegated".

Model names and model ids are masked as "[model]" in every text field.
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
    s = mfrlib.mask_models((s or "").strip())
    if len(s) <= n:
        return s
    return ("…" + s[-n:]) if tail else (s[:n] + "…")


def build(messages: list[dict], runs: list[dict], seed: int = 7) -> tuple[list[dict], dict]:
    text = {m["id"]: m["text"] for m in messages}
    pairs = mfrlib.reaction_items(runs, text)
    rng = random.Random(seed)
    rng.shuffle(pairs)
    items, key = [], {}
    for i, (r, mid, kind) in enumerate(pairs):
        iid = f"i{i:05d}"
        items.append({"id": iid, "kind": kind, "request": cut(r["request"], 400),
                      "assistant_reply_end": cut(r.get("reply_end"), 700, tail=True) if kind == "reaction" else "",
                      "next_user_message": cut(text.get(mid), 400)})
        key[iid] = {"message_id": mid, "run_id": r["run_id"], "kind": kind}
    return items, key


def calibration(items: list[dict], n: int, seed: int) -> list[dict]:
    return mfrlib.sample([it for it in items if it["kind"] == "reaction"], n, seed + 1)


def build_episodes(episodes: list[dict], runs: list[dict], seed: int = 7) -> tuple[list[dict], dict]:
    by_id = {r["run_id"]: r for r in runs}
    rows = []
    for ep in episodes:
        own = [by_id[i] for i in ep["run_ids"] if i in by_id]
        reqs = [r["request"] for r in own if r.get("initiator", "human") == "human"]
        # A delegated episode (every run agent-initiated) is described by its briefs.
        source = "user" if reqs else "delegated"
        reqs = reqs or [r["request"] for r in own]
        rows.append((ep["episode"], reqs, source))
    random.Random(seed).shuffle(rows)
    items, key = [], {}
    for i, (eid, reqs, source) in enumerate(rows):
        iid = f"e{i:05d}"
        items.append({"id": iid, "source": source, "requests": [cut(q, 220) for q in reqs[:6]],
                      "n_requests": len(reqs)})
        key[iid] = {"episode": eid}
    return items, key


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--calib", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--episodes", action="store_true", help="export task-type items per episode")
    a = ap.parse_args()
    d = Path(a.data)
    runs = mfrlib.read_jsonl(d / "runs.jsonl")
    if a.episodes:
        items, key = build_episodes(mfrlib.read_jsonl(d / "episodes.jsonl"), runs, a.seed)
        calib = mfrlib.sample(items, a.calib, a.seed + 1)
        mfrlib.write_jsonl(d / "episode_items.jsonl", items)
        mfrlib.write_jsonl(d / "episode_calib.jsonl", calib)
        (d / "episode_key.json").write_text(json.dumps(key), encoding="utf-8")
        print(f"{len(items)} episode items; {len(calib)} in episode_calib.jsonl")
        return 0
    items, key = build(mfrlib.read_jsonl(d / "messages.jsonl"), runs, a.seed)
    calib = calibration(items, a.calib, a.seed)
    mfrlib.write_jsonl(d / "items.jsonl", items)
    mfrlib.write_jsonl(d / "calib.jsonl", calib)
    (d / "key.json").write_text(json.dumps(key), encoding="utf-8")
    n_react = sum(1 for it in items if it["kind"] == "reaction")
    print(f"{len(items)} items ({n_react} reaction, {len(items) - n_react} steer); "
          f"{len(calib)} reaction items in calib.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
