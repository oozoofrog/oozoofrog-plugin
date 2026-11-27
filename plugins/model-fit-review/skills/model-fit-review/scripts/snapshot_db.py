#!/usr/bin/env python3
"""Copy a SQLite DB (for example the T3 Code state DB) read-only to a snapshot.

Usage: snapshot_db.py --source <statev2.sqlite> --dest <dir-or-file> [--yes] [--force]
       snapshot_db.py --delete <snapshot.sqlite>

The source is opened read-only (`file:<percent-encoded path>?mode=ro`) and
copied with the SQLite online backup API, so no shell quoting is involved.
After the copy the snapshot is switched to journal_mode=DELETE: readers then
create no `-wal` or `-shm` files next to it.

The copy can be several GB. The script checks free space at the destination
(source size + 10 %) and asks before copying. Pass --yes in a non-interactive
run (an agent's shell has no terminal to answer the prompt). An existing
snapshot is kept unless --force is given.

--delete removes a snapshot and any `-wal`, `-shm` or `-journal` file next to
it. Use it at hand-back, after the user agrees. SQLite temporary files go to
SQLITE_TMPDIR or TMPDIR.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mfrlib  # noqa: E402

SIDECARS = ("-wal", "-shm", "-journal")


def plan(source: Path, dest: Path) -> tuple[Path, int, int]:
    if dest.is_dir() or not dest.suffix:
        dest = dest / "t3state.sqlite"
    need = int(source.stat().st_size * 1.1)
    probe = dest.parent
    while not probe.exists():
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    return dest, need, free


def remove(path: Path) -> list[Path]:
    """Delete a snapshot and its sidecar files. Returns the paths removed."""
    gone = []
    for p in [path] + [Path(str(path) + s) for s in SIDECARS]:
        if p.exists():
            p.unlink()
            gone.append(p)
    return gone


def copy(source: Path, dest: Path, force: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or any(Path(str(dest) + s).exists() for s in SIDECARS):
        if not force:
            raise SystemExit(f"refusing to overwrite {dest}; pass --force to replace it")
        remove(dest)
    src = sqlite3.connect(mfrlib.ro_uri(source), uri=True)
    dst = sqlite3.connect(str(dest))
    try:
        src.backup(dst)
        dst.execute("pragma journal_mode=DELETE")
    finally:
        dst.close()
        src.close()
    for s in ("-wal", "-shm"):
        Path(str(dest) + s).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source")
    ap.add_argument("--dest")
    ap.add_argument("--yes", action="store_true", help="copy without asking (needed in a non-interactive shell)")
    ap.add_argument("--force", action="store_true", help="replace an existing snapshot at --dest")
    ap.add_argument("--allow-repo", action="store_true", help="allow a destination inside a git work tree")
    ap.add_argument("--delete", metavar="SNAPSHOT", help="delete a snapshot and its -wal/-shm files, then exit")
    a = ap.parse_args()
    if a.delete:
        gone = remove(Path(a.delete).expanduser())
        print("deleted: " + (", ".join(str(p) for p in gone) if gone else "nothing (no such files)"))
        return 0
    if not a.source or not a.dest:
        ap.error("--source and --dest are required (or use --delete)")
    source = Path(a.source).expanduser()
    if not source.is_file():
        print(f"source not found: {source}", file=sys.stderr)
        return 2
    dest, need, free = plan(source, Path(a.dest).expanduser())
    err = mfrlib.check_output_dir(dest.parent, a.allow_repo)
    if err:
        print(err, file=sys.stderr)
        return 2
    gb = 1024 ** 3
    print(f"source {source} ({source.stat().st_size / gb:.2f} GB) -> {dest}")
    print(f"needs about {need / gb:.2f} GB; free at destination {free / gb:.2f} GB")
    if free < need:
        print("not enough free space; choose another destination", file=sys.stderr)
        return 2
    if not a.yes:
        try:
            if input("copy now? [y/N] ").strip().lower() != "y":
                return 1
        except EOFError:
            print("no terminal to confirm; pass --yes to copy without asking", file=sys.stderr)
            return 1
    copy(source, dest, a.force)
    print(f"snapshot written: {dest} ({os.path.getsize(dest) / gb:.2f} GB), journal_mode=DELETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
