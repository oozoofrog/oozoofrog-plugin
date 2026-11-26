#!/usr/bin/env python3
"""Create or update a project-wiki vault. Safe to run again.

Usage:
  wiki_init.py [--project DIR] [--vault DIR] [--lang ko] [--name NAME] [--dry-run]
  wiki_init.py --global DIR [--lang ko] [--dry-run]     cross-project lesson vault

Rules for each bundled file:
  missing                          -> write it
  unchanged since init wrote it    -> replace it with the new bundled version
  edited by the user, or pre-existing with other content -> keep it, report "kept"
Notes the user or an agent wrote are never touched. `.wiki/config.json` is
written only when missing. Prints one JSON object.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets" / "vault"
USER_CONFIG = Path(os.environ.get("PROJECT_WIKI_CONFIG", Path.home() / ".config" / "project-wiki" / "config.json"))

FOLDERS = {
    "ko": {
        "dashboards": "00 대시보드", "episodes": "10 작업 기록", "lessons": "20 교훈",
        "instruction_guide": "30 지시 가이드", "response_guide": "40 대응 가이드",
        "knowledge": "50 지식", "retros": "60 회고", "templates": "90 템플릿",
    },
}
GLOBAL_KEEP = {"dashboards", "lessons", "templates"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def render(rel: str, raw: bytes, name: str) -> bytes:
    # Templates keep Obsidian's {{date}} and {{title}}; only {{project}} is ours.
    if rel.endswith((".md", ".base")):
        return raw.decode("utf-8").replace("{{project}}", name).encode("utf-8")
    return raw


def bundled(lang: str, kind: str, folders: dict):
    src = ASSETS / lang
    for f in sorted(src.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(src).as_posix()
        top = rel.split("/", 1)[0]
        if kind == "global":
            keep = {folders[k] for k in GLOBAL_KEEP} | {".obsidian"}
            if top not in keep or rel.endswith(("작업 기록.base", "지식.base")) or ("템플릿" in rel and "교훈" not in rel):
                continue
        yield rel, f.read_bytes()


def install(vault: Path, lang: str, kind: str, name: str, dry: bool) -> dict:
    folders = FOLDERS[lang]
    meta = vault / ".wiki"
    manifest_path = meta / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    result = {"created": [], "updated": [], "kept": [], "unchanged": []}
    for rel, raw in bundled(lang, kind, folders):
        data = render(rel, raw, name)
        dest = vault / rel
        new_hash = sha(data)
        if not dest.exists():
            result["created"].append(rel)
            if not dry:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            manifest[rel] = new_hash
            continue
        cur = sha(dest.read_bytes())
        if cur == new_hash:
            result["unchanged"].append(rel)
            manifest[rel] = new_hash
        elif manifest.get(rel) == cur:
            result["updated"].append(rel)
            if not dry:
                dest.write_bytes(data)
            manifest[rel] = new_hash
        else:
            result["kept"].append(rel)  # the user's version wins; manifest keeps the old hash
    wanted = folders if kind == "project" else {k: v for k, v in folders.items() if k in GLOBAL_KEEP}
    made = [d for d in wanted.values() if not (vault / d).is_dir()]
    cfg_path = meta / "config.json"
    cfg_new = not cfg_path.is_file()
    if not dry:
        for d in wanted.values():
            (vault / d).mkdir(parents=True, exist_ok=True)
        meta.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if cfg_new:
            cfg = {"schema_version": 1, "kind": kind, "lang": lang, "project": name,
                   "folders": wanted, "created": date.today().isoformat()}
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["folders_created"] = made
    result["config"] = "created" if cfg_new else "kept"
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project")
    ap.add_argument("--vault")
    ap.add_argument("--global", dest="global_vault")
    ap.add_argument("--lang", default="ko", choices=sorted(FOLDERS))
    ap.add_argument("--name")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    out = {"ok": True, "dry_run": a.dry_run}
    if a.global_vault:
        vault = Path(a.global_vault).expanduser().resolve()
        kind, name, root = "global", a.name or "공통", None
    else:
        start = Path(a.project or os.getcwd()).resolve()
        top = git(start, "rev-parse", "--show-toplevel").stdout.strip()
        root = Path(top) if top else start
        if root == Path.home():
            print(json.dumps({"ok": False, "error": "refusing to create a vault for the home folder"}))
            return 2
        vault = Path(a.vault).resolve() if a.vault else root / "_context" / "wiki"
        kind, name = "project", a.name or root.name
        out["project"] = str(root)
    anchor = vault if vault.exists() else next(p for p in vault.parents if p.exists())
    if not os.access(anchor, os.W_OK):
        print(json.dumps({"ok": False, "error": f"not writable: {anchor}"}))
        return 2
    out["vault"] = str(vault)
    out["kind"] = kind
    out.update(install(vault, a.lang, kind, name, a.dry_run))
    if root is not None and top:
        rel = os.path.relpath(vault, root)
        inside = not rel.startswith("..")
        out["inside_repo"] = inside
        if inside:
            # check-ignore needs a path; the folder itself may not exist yet in dry-run
            out["git_ignored"] = git(root, "check-ignore", "-q", rel + "/").returncode == 0
    if kind == "global" and not a.dry_run:
        USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        cfg = json.loads(USER_CONFIG.read_text(encoding="utf-8")) if USER_CONFIG.is_file() else {}
        cfg["global_vault"] = str(vault)
        USER_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out["user_config"] = str(USER_CONFIG)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
