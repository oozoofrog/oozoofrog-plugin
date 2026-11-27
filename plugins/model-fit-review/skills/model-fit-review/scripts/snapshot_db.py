#!/usr/bin/env python3
"""Copy a SQLite DB (for example the T3 Code state DB) read-only to a snapshot.

Usage: snapshot_db.py --source <statev2.sqlite> --dest <dir-or-file> [--yes]

The source is opened with mode=ro and copied with the SQLite backup command:
  sqlite3 "file:<source>?mode=ro" ".backup <dest>"
The copy can be several GB. The script checks free space at the destination
(source size + 10 %) and asks before copying unless --yes is given.
Delete the snapshot when the review ends; offer that to the user.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


def plan(source: Path, dest: Path) -> tuple[Path, int, int]:
    if dest.is_dir() or not dest.suffix:
        dest = dest / "t3state.sqlite"
    need = int(source.stat().st_size * 1.1)
    probe = dest.parent
    while not probe.exists():
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    return dest, need, free


def copy(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise SystemExit(f"refusing to overwrite {dest}")
    uri = f"file:{source}?mode=ro"
    if shutil.which("sqlite3"):
        subprocess.run(["sqlite3", uri, f".backup '{dest}'"], check=True)
    else:
        src = sqlite3.connect(uri, uri=True)
        dst = sqlite3.connect(dest)
        src.backup(dst)
        dst.close()
        src.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    source = Path(a.source).expanduser()
    dest, need, free = plan(source, Path(a.dest).expanduser())
    gb = 1024 ** 3
    print(f"source {source} ({source.stat().st_size / gb:.2f} GB) -> {dest}")
    print(f"needs about {need / gb:.2f} GB; free at destination {free / gb:.2f} GB")
    if free < need:
        print("not enough free space; choose another destination", file=sys.stderr)
        return 2
    if not a.yes and input("copy now? [y/N] ").strip().lower() != "y":
        return 1
    copy(source, dest)
    print(f"snapshot written: {dest} ({os.path.getsize(dest) / gb:.2f} GB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
