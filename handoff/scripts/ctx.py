"""Handoff helper for the skill.

  ctx.py prepare [--cwd DIR] [--allow-non-git]   create _context/, prune, archive the previous handoff, print paths
  ctx.py validate PATH                           check frontmatter, current branch/HEAD, sections, and size limit
  ctx.py set-status active|done [--cwd DIR]      done: mark finished and move the handoff to sessions/
  ctx.py prune [--cwd DIR]                       archive finished/orphaned handoffs, expire old archives
  ctx.py status [--cwd DIR]                      show where the handoff lives, its frontmatter, and staleness
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctxlib  # noqa: E402


def out(obj: dict, code: int = 0) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(code)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--cwd", default=os.getcwd())
    p.add_argument("--allow-non-git", action="store_true")
    v = sub.add_parser("validate")
    v.add_argument("path")
    s = sub.add_parser("set-status")
    s.add_argument("status", choices=ctxlib.STATUSES)
    s.add_argument("--cwd", default=os.getcwd())
    for name in ("prune", "status"):
        sub.add_parser(name).add_argument("--cwd", default=os.getcwd())
    a = ap.parse_args()

    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if a.cmd == "prepare":
        r = ctxlib.prepare(a.cwd, a.allow_non_git, sid)
        out(r, 0 if r["ok"] else 1)
    if a.cmd == "validate":
        path = Path(a.path).resolve()
        r = ctxlib.validate(path, ctxlib.find_root(path.parent), sid)
        out(r, 0 if r["ok"] else 1)

    root = ctxlib.find_root(a.cwd)
    if not root:
        out({"ok": False, "error": "프로젝트 루트를 찾지 못했습니다."}, 1)
    path = ctxlib.handoff_path(root, ctxlib.branch_name(root))
    if a.cmd == "prune":
        out({"ok": True, **ctxlib.prune(root)})
    if a.cmd == "status":
        info = {"ok": True, "root": str(root), "handoff_path": str(path), "exists": path.is_file()}
        if path.is_file():
            fm, _ = ctxlib.parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
            info["frontmatter"] = fm
            info["stale"] = ctxlib.staleness(root, fm, path) if fm else ["frontmatter 없음"]
            info["tracked_by_git"] = ctxlib.is_tracked(root, path)
        out(info)
    if a.cmd == "set-status":
        if a.status == "done":
            r = ctxlib.done(root)
            out(r, 0 if r["ok"] else 1)
        if not path.is_file():
            out({"ok": False, "error": f"인계 문서가 없습니다: {path}"}, 1)
        text = path.read_text(encoding="utf-8")
        text = ctxlib.set_frontmatter_value(text, "status", "active")
        text = ctxlib.set_frontmatter_value(text, "updated", ctxlib.now_local().isoformat(timespec="seconds"))
        ctxlib.atomic_write(path, text)
        out({"ok": True, "handoff_path": str(path), "status": "active"})


if __name__ == "__main__":
    main()
