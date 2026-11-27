#!/usr/bin/env python3
"""Group runs into episodes and count reactions per episode.

Usage: episodes.py --data <dir> [--labels labels.json ...]
Reads <dir>/messages.jsonl, <dir>/runs.jsonl, <dir>/key.json and label files
({item_id: label}, from hand labels or calibrated classifiers). Writes
<dir>/episodes.jsonl. Labels are keyed by message id, so they survive a
rebuild of runs or episodes. Rerunning on the same input gives identical output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402


def message_labels(key: dict, label_files: list[dict]) -> dict[str, str]:
    out = {}
    for labels in label_files:
        for iid, lab in labels.items():
            if iid in key:
                out[key[iid]["message_id"]] = lab
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--labels", nargs="*", default=[])
    a = ap.parse_args()
    d = Path(a.data)
    messages = mfrlib.read_jsonl(d / "messages.jsonl")
    runs = mfrlib.read_jsonl(d / "runs.jsonl")
    key = json.loads((d / "key.json").read_text(encoding="utf-8")) if (d / "key.json").exists() else {}
    labels = message_labels(key, [json.loads(Path(p).read_text(encoding="utf-8")) for p in a.labels])
    texts = {m["id"]: m["text"] for m in messages}
    eps = mfrlib.group_episodes(runs, labels, texts)
    mfrlib.write_jsonl(d / "episodes.jsonl", eps)
    unlabeled = sum(1 for r in runs if r["follow_state"] == "reaction" and r["reaction_id"] not in labels
                    and not mfrlib.is_control(texts.get(r["reaction_id"])))
    print(f"runs {len(runs)}  episodes {len(eps)}  unlabeled reactions {unlabeled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
