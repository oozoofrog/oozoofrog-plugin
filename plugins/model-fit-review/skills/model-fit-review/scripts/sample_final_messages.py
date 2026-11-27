#!/usr/bin/env python3
"""Sample final assistant messages of main-session turns from Claude Code logs.

Usage: sample_final_messages.py --out <file.jsonl> [--projects ~/.claude/projects]
       [--since 2026-01-01] [--n 50] [--seed 7] [--pattern REGEX]

Use it to dry-run a proposed check (for example a Stop hook) on real turn
endings before installing anything. Half of the sample matches --pattern in
the last 600 characters (default: question-like endings), half does not.
Output rows: {id, file, ts, last_assistant_message}. Keep the output local;
it holds message text.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402
from extract_logs import session_files  # noqa: E402

DEFAULT_PATTERN = r"(\?|까요|주세요|알려 주|정해 주|골라 주|말씀해)"


def finals(projects: Path, since: str) -> list[tuple[str, str, str]]:
    out = []
    for p in session_files(projects):
        last = None
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if mfrlib.prompt_kind(d)[0] is not None:  # any prompt (human or injected) ends a turn
                    if last:
                        out.append(last)
                    last = None
                elif d.get("type") == "assistant" and not d.get("isSidechain"):
                    ts = d.get("timestamp") or ""
                    t = "\n".join(x.get("text", "") for x in (d.get("message") or {}).get("content") or []
                                  if isinstance(x, dict) and x.get("type") == "text").strip()
                    if t and ts >= since:
                        last = (str(p), ts, t)
        if last:
            out.append(last)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--projects", default=str(Path.home() / ".claude" / "projects"))
    ap.add_argument("--since", default="")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--pattern", default=DEFAULT_PATTERN)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rx = re.compile(a.pattern)
    all_finals = finals(Path(a.projects).expanduser(), a.since)
    hit = [x for x in all_finals if rx.search(x[2][-600:])]
    miss = [x for x in all_finals if not rx.search(x[2][-600:])]
    rng = random.Random(a.seed)
    half = a.n // 2
    pick = rng.sample(hit, min(half, len(hit))) + rng.sample(miss, min(a.n - half, len(miss)))
    rng.shuffle(pick)
    mfrlib.write_jsonl(a.out, ({"id": f"n{i:02d}", "file": f, "ts": ts, "last_assistant_message": t[-6000:]}
                               for i, (f, ts, t) in enumerate(pick)))
    print(f"turn finals {len(all_finals)}  pattern hits {len(hit)}  sampled {len(pick)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
