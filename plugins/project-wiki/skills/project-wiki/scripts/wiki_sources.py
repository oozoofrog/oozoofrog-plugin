#!/usr/bin/env python3
"""Find wiki source material that is new since the last ingest.

Usage (run inside the project, or pass --project):
  wiki_sources.py status  [--vault DIR]          list new material per source, write .wiki/pending.json
  wiki_sources.py prompts [--vault DIR] [--all]  print the owner's prompts from new transcript parts
  wiki_sources.py mark    [--vault DIR] [--source KEY ...] [--t3 ISO]
                                                 accept pending.json as ingested (move the watermark)

The watermark moves only on `mark`, so a failed or partial ingest is read again
next time. Reads only; `status` and `mark` write inside <vault>/.wiki/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
BYTES_PER_TOKEN = 3.5  # rough average for mixed Korean/English text; for estimates only

# Prompts that an agent or a tool sent, not the owner. Prefix match after strip().
SKIP_PREFIXES = (
    "<command-", "<local-command", "<system-reminder", "<task-notification", "<bash-",
    "<environment_context", "<user_instructions", "# AGENTS.md instructions",
    "Caveat:", "[Request interrupted", "This session is being continued",
    "Base directory for this skill", "Delegated task node", "Act as the implementation sub-",
    "Coordination", "Collaboration request", "[T3 Code: the agent", "Act as the ",
    "Continue the same task", "Background command completed", "Context handoff",
)
SKIP_EXACT = {"Retry", "Resume", "Continue", "Model changed retry"}


def die(msg: str, code: int = 2):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(code)


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def encode(p: str) -> str:
    # Claude Code names a project folder after its path with "/" and "." replaced by "-".
    return re.sub(r"[/.]", "-", p)


def project_root(arg: str | None) -> Path:
    start = Path(arg or os.getcwd()).resolve()
    top = git(start, "rev-parse", "--show-toplevel")
    return Path(top) if top else start


FORMER: list[str] = []  # set from .wiki/config.json "former_paths" (renamed or moved project)


def worktree_paths(root: Path) -> list[str]:
    out = [str(root), *FORMER]
    for line in git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            out.append(line[9:])
    return sorted(set(out))


def claude_project_dirs(root: Path) -> list[Path]:
    base = HOME / ".claude" / "projects"
    if not base.is_dir():
        return []
    prefixes = {encode(p) for p in worktree_paths(root)}
    names = {root.name, *(Path(f).name for f in FORMER)}
    t3s = [f"-t3-worktrees-{encode(n)}-" for n in names]  # T3 worktrees deleted after their thread ended
    found = []
    for d in base.iterdir():
        if not d.is_dir():
            continue
        n = d.name
        if n in prefixes or any(n.startswith(p + ".") for p in prefixes) or any(t in n for t in t3s):
            found.append(d)
    return sorted(found)


def codex_session_files(root: Path, include_t3: bool = False) -> list[Path]:
    """Codex sessions for this project. Sessions that T3 Code started are skipped by
    default: their transcripts cannot tell the owner's messages from delegated briefs,
    and the T3 thread history (read by the agent) records who wrote each message."""
    homes = [Path(os.environ.get("CODEX_HOME", HOME / ".codex"))]
    homes += sorted((HOME / ".t3" / "userdata" / "codex-accounts").glob("*"))
    roots = worktree_paths(root)
    t3s = [f"/.t3/worktrees/{Path(n).name}/" for n in (str(root), *FORMER)]
    out = []
    for h in homes:
        for f in sorted((h / "sessions").rglob("rollout-*.jsonl")) if (h / "sessions").is_dir() else []:
            try:
                with f.open(encoding="utf-8", errors="replace") as fh:
                    meta = json.loads(fh.readline())
            except (OSError, ValueError):
                continue
            pl = meta.get("payload") or {}
            cwd = pl.get("cwd") or ""
            if pl.get("thread_source") == "subagent" or (pl.get("originator") == "T3 Code" and not include_t3):
                continue
            if any(cwd == r or cwd.startswith(r + "/") for r in roots) or any(t in cwd for t in t3s):
                out.append(f)
    return out


def file_sig(p: Path) -> dict:
    st = p.stat()
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def vault_path(root: Path, arg: str | None) -> Path:
    v = Path(arg).resolve() if arg else root / "_context" / "wiki"
    cfg = v / ".wiki" / "config.json"
    if not cfg.is_file():
        die(f"no project-wiki vault at {v} (missing .wiki/config.json); run wiki_init.py first")
    FORMER[:] = json.loads(cfg.read_text(encoding="utf-8")).get("former_paths", [])
    return v


def load_state(v: Path) -> dict:
    p = v / ".wiki" / "state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"version": 1, "sources": {}}


def save_json(p: Path, data: dict):
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


# ---------------------------------------------------------------- sources
# Each source returns {key: {"kind", "path", "new_bytes", "cursor", ...}}.
# Append-only transcripts use a byte offset; documents use size+mtime; git uses a commit.


def transcript_items(files, kind, state):
    items = {}
    for f in files:
        key = f"{kind}:{f}"
        old = state.get(key, {})
        size = f.stat().st_size
        start = old.get("offset", 0) if old.get("offset", 0) <= size else 0
        if size > start:
            items[key] = {"kind": kind, "path": str(f), "from": start, "cursor": {"offset": size},
                          "new_bytes": size - start}
    return items


def document_items(paths, kind, state):
    items = {}
    for f in paths:
        key = f"{kind}:{f}"
        sig = file_sig(f)
        if state.get(key) != sig:
            items[key] = {"kind": kind, "path": str(f), "cursor": sig, "new_bytes": sig["size"],
                          "changed": key in state}
    return items


def collect(root: Path, v: Path, state: dict, include_t3_codex: bool = False) -> dict:
    s = state["sources"]
    items = {}
    cdirs = claude_project_dirs(root)
    items.update(transcript_items([f for d in cdirs for f in sorted(d.glob("*.jsonl"))], "claude", s))
    items.update(transcript_items(codex_session_files(root, include_t3_codex), "codex", s))
    ctx = root / "_context"
    docs = sorted((ctx / "sessions").glob("*.md")) + sorted((ctx / "handoff").glob("*.md")) if ctx.is_dir() else []
    items.update(document_items(docs, "handoff", s))
    items.update(document_items(memory_files(root, cdirs), "memory", s))
    head = git(root, "rev-parse", "HEAD")
    last = s.get("git", {}).get("commit")
    if head and head != last:
        rng = f"{last}..HEAD" if last and git(root, "cat-file", "-t", last) else "HEAD"
        n = git(root, "rev-list", "--count", rng)
        items["git"] = {"kind": "git", "path": str(root), "range": rng, "commits": int(n or 0),
                        "cursor": {"commit": head}, "new_bytes": 0}
    return items


def memory_files(root: Path, cdirs: list[Path]) -> list[Path]:
    """One file per memory name. Worktree and former-path folders hold copies of the same
    rules; prefer the current project's folder, then the newest copy."""
    own = encode(str(root))
    best: dict[str, Path] = {}
    for d in cdirs:
        for f in sorted((d / "memory").glob("*.md")):
            cur = best.get(f.name)
            rank = (d.name == own, f.stat().st_mtime)
            if cur is None or rank > (cur.parent.parent.name == own, cur.stat().st_mtime):
                best[f.name] = f
    return sorted(best.values())


def cmd_status(a):
    root = project_root(a.project)
    v = vault_path(root, a.vault)
    state = load_state(v)
    items = collect(root, v, state, a.include_t3_codex)
    by_kind = {}
    for it in items.values():
        k = by_kind.setdefault(it["kind"], {"items": 0, "new_bytes": 0})
        k["items"] += 1
        k["new_bytes"] += it["new_bytes"]
    for k in by_kind.values():
        k["est_tokens_raw"] = int(k["new_bytes"] / BYTES_PER_TOKEN)
    pending = {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "items": items}
    pp = v / ".wiki" / "pending.json"
    if items:
        save_json(pp, pending)
    elif pp.exists():
        pp.unlink()
    print(json.dumps({
        "ok": True, "project": str(root), "vault": str(v),
        "first_ingest": not state["sources"], "summary": by_kind,
        "t3_last_ingest": state["sources"].get("t3", {}).get("updated_at"),
        "claude_project_dirs": [str(d) for d in claude_project_dirs(root)],
        "documents": sorted(it["path"] for it in items.values() if it["kind"] in ("handoff", "memory")),
        "git": items.get("git"),
        "pending": str(v / ".wiki" / "pending.json"),
    }, ensure_ascii=False, indent=2))


def read_from(path: str, offset: int):
    with open(path, "rb") as fh:
        fh.seek(offset)
        if offset:
            fh.readline()  # the offset is a line end; skip a partial line defensively
        for raw in fh:
            try:
                yield json.loads(raw)
            except ValueError:
                continue


def owner_texts(entry: dict, kind: str):
    if kind == "claude":
        if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isCompactSummary"):
            return []
        c = (entry.get("message") or {}).get("content")
        if isinstance(c, str):
            return [c]
        return [b.get("text", "") for b in c or [] if isinstance(b, dict) and b.get("type") == "text"]
    p = entry.get("payload") or {}
    if entry.get("type") == "response_item" and p.get("type") == "message" and p.get("role") == "user":
        return [b.get("text", "") for b in p.get("content") or [] if isinstance(b, dict) and b.get("type") == "input_text"]
    return []


def cmd_prompts(a):
    root = project_root(a.project)
    v = vault_path(root, a.vault)
    if a.all:
        items = collect(root, v, {"sources": {}}, a.include_t3_codex)
    else:
        p = v / ".wiki" / "pending.json"
        if not p.is_file():
            die("no pending.json; run `status` first")
        items = json.loads(p.read_text(encoding="utf-8"))["items"]
    out, seen = [], set()
    for it in items.values():
        if it["kind"] not in ("claude", "codex"):
            continue
        sid = Path(it["path"]).stem[-36:][:8] if it["kind"] == "codex" else Path(it["path"]).stem[:8]
        for e in read_from(it["path"], 0 if a.all else it.get("from", 0)):
            for t in owner_texts(e, it["kind"]):
                t = re.sub(r"<system-reminder>.*?</system-reminder>", "", t or "", flags=re.S).strip()
                if not t or t.startswith(SKIP_PREFIXES) or t in SKIP_EXACT:
                    continue
                h = hashlib.sha1(t[:200].encode()).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                ts = (e.get("timestamp") or "")[:16]
                out.append((ts, it["kind"][0], sid, t.replace("\n", " ⏎ ")[: a.width]))
    for ts, k, sid, t in sorted(out):
        print(f"{ts} {k}:{sid} | {t}")
    print(f"# {len(out)} prompt(s). Times are UTC.", file=sys.stderr)


def cmd_mark(a):
    root = project_root(a.project)
    v = vault_path(root, a.vault)
    state = load_state(v)
    p = v / ".wiki" / "pending.json"
    marked = []
    if p.is_file():
        items = json.loads(p.read_text(encoding="utf-8"))["items"]
        for key, it in items.items():
            if a.source and it["kind"] not in a.source:
                continue
            state["sources"][key] = it["cursor"]
            marked.append(key)
        rest = {k: x for k, x in items.items() if k not in marked}
        if rest:
            save_json(p, {"items": rest})
        else:
            p.unlink()
    if a.t3:
        state["sources"]["t3"] = {"updated_at": a.t3}
        marked.append("t3")
    state["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_json(v / ".wiki" / "state.json", state)
    print(json.dumps({"ok": True, "marked": len(marked), "kinds": sorted({m.split(":")[0] for m in marked})}))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "prompts", "mark"):
        sp = sub.add_parser(name)
        sp.add_argument("--project")
        sp.add_argument("--vault")
        if name in ("status", "prompts"):
            sp.add_argument("--include-t3-codex", action="store_true",
                            help="also read Codex sessions started by T3 Code (usually covered by T3 threads)")
        if name == "prompts":
            sp.add_argument("--all", action="store_true", help="ignore the watermark")
            sp.add_argument("--width", type=int, default=600)
        if name == "mark":
            sp.add_argument("--source", action="append", choices=["claude", "codex", "handoff", "memory", "git"])
            sp.add_argument("--t3", help="ISO time of the newest T3 thread update you ingested")
    a = ap.parse_args(argv)
    {"status": cmd_status, "prompts": cmd_prompts, "mark": cmd_mark}[a.cmd](a)


if __name__ == "__main__":
    main()
