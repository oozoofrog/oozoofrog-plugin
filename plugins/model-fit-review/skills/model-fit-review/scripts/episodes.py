#!/usr/bin/env python3
"""Group runs into episodes and count reactions per episode.

Usage: episodes.py --data <dir> [--hand labels_hand.json ...]
       [--labels labels_haiku_1.json ...] [--exclude-thread ID ...]

Reads <dir>/messages.jsonl, <dir>/runs.jsonl, <dir>/key.json and label files
({item_id: label}). Writes <dir>/episodes.jsonl. Labels are keyed by message
id and item kind, so they survive a rebuild of runs or episodes.

Precedence: a hand label always wins over a classifier label for the same
item, whatever the order of the files on the command line. Files given with
--hand are hand labels; so is any --labels file whose name starts with
"labels_hand". Among classifier files, a later file wins.

--exclude-thread drops a thread (for example the review's own session).
Rerunning on the same input gives identical output.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402


def message_labels(key: dict, label_files: list[dict], hand_files: list[dict] | None = None
                   ) -> dict[str, dict[str, str]]:
    """{"reaction": {message_id: label}, "steer": {message_id: label}}.
    Classifier files are applied first, then hand files, so hand labels win."""
    out: dict[str, dict[str, str]] = {"reaction": {}, "steer": {}}
    for labels in list(label_files) + list(hand_files or []):
        for iid, lab in labels.items():
            if iid in key:
                k = key[iid]
                out[k.get("kind", "reaction")][k["message_id"]] = lab
    return out


def load_labels(hand: list[str], labels: list[str]) -> tuple[list[dict], list[dict]]:
    """(classifier files, hand files) as dicts. A --labels file named
    labels_hand*.json counts as a hand file."""
    hand_paths = list(hand) + [p for p in labels if Path(p).name.startswith("labels_hand")]
    clf_paths = [p for p in labels if not Path(p).name.startswith("labels_hand")]
    read = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
    return [read(p) for p in clf_paths], [read(p) for p in hand_paths]


def unlabeled_reactions(runs: list[dict], texts: dict[str, str], labels: dict[str, str]) -> int:
    """Reaction items (same rule as export_items) that have no label. Runs whose
    request is a session command export no item, so they are not counted."""
    return sum(1 for _, mid, kind in mfrlib.reaction_items(runs, texts)
               if kind == "reaction" and mid not in labels)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--hand", nargs="*", default=[], help="hand-label files (always win)")
    ap.add_argument("--labels", nargs="*", default=[], help="classifier label files")
    ap.add_argument("--exclude-thread", nargs="*", default=[], help="thread ids to leave out")
    a = ap.parse_args()
    d = Path(a.data)
    messages = mfrlib.read_jsonl(d / "messages.jsonl")
    runs = mfrlib.read_jsonl(d / "runs.jsonl")
    key = json.loads((d / "key.json").read_text(encoding="utf-8")) if (d / "key.json").exists() else {}
    clf, hand = load_labels(a.hand, a.labels)
    labels = message_labels(key, clf, hand)
    texts = {m["id"]: m["text"] for m in messages}
    eps = mfrlib.group_episodes(runs, labels["reaction"], texts, labels["steer"], a.exclude_thread)
    mfrlib.write_jsonl(d / "episodes.jsonl", eps)
    kept = [r for r in runs if r["thread"] not in set(a.exclude_thread)]
    print(f"runs {len(kept)}  episodes {len(eps)}  unlabeled reactions "
          f"{unlabeled_reactions(kept, texts, labels['reaction'])}  hand files {len(hand)}  classifier files {len(clf)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
