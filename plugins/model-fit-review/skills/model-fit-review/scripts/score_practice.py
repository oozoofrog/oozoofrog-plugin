#!/usr/bin/env python3
"""Score a practice round: right picks, over-picks and under-picks.

Usage: score_practice.py --cards cards.json --picks picks.json --round 1
cards.json: list of cards with "id", "round", "reference" (list of model
families) and "evidence" (replay / observed / inferred).
picks.json: {card_id: family}. A pick is right when it is in the reference set.
An over-pick is above the highest reference model; an under-pick is below the
lowest. Effort is not scored. The scores are only as good as the references.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ORDER = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}


def score(cards: list[dict], picks: dict[str, str], rnd: int) -> dict:
    rows = []
    for c in cards:
        if c.get("round") != rnd or c["id"] not in picks:
            continue
        pick = picks[c["id"]].lower()
        ref = [r.lower() for r in c["reference"]]
        lo, hi = min(ORDER[r] for r in ref), max(ORDER[r] for r in ref)
        side = "right" if pick in ref else ("over" if ORDER[pick] > hi else ("under" if ORDER[pick] < lo else "between"))
        rows.append({"card": c["id"], "pick": pick, "reference": ref, "evidence": c.get("evidence"), "result": side})
    count = lambda k: sum(1 for r in rows if r["result"] == k)
    by_evidence = {}
    for r in rows:
        e = by_evidence.setdefault(r["evidence"] or "unknown", {"n": 0, "right": 0})
        e["n"] += 1
        e["right"] += r["result"] == "right"
    return {"round": rnd, "n": len(rows), "right": count("right"), "over": count("over"),
            "under": count("under"), "between": count("between"), "by_evidence": by_evidence, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cards", required=True)
    ap.add_argument("--picks", required=True)
    ap.add_argument("--round", type=int, required=True)
    a = ap.parse_args()
    result = score(json.loads(Path(a.cards).read_text(encoding="utf-8")),
                   json.loads(Path(a.picks).read_text(encoding="utf-8")), a.round)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
