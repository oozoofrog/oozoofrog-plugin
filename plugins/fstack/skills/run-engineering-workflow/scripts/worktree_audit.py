"""Inventory worktrees. Activity snapshots are PATH<TAB>active|inactive|unknown."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def run(args, cwd):
    try:
        p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return None
    return os.fsdecode(p.stdout) if p.returncode == 0 else None


def git(cwd, *args):
    return run(["git", *args], cwd)


def activity_file(path):
    rows = {}
    if path:
        for line in path.read_text().splitlines():
            name, tab, state = line.rpartition("\t")
            if not tab or not Path(name).is_absolute() or state not in ("active", "inactive", "unknown"):
                raise ValueError("invalid activity record")
            key = Path(name).resolve()
            if key in rows:
                raise ValueError(f"duplicate activity record: {key}")
            rows[key] = state
    return rows


def pr_status(repo, branch, remote):
    if not branch or remote == "":
        return "-", "none"
    if remote is None:
        return "?", "unknown"
    # Query by head instead of restricting ownership or relying on a global page limit.
    for cmd, fields in [(["origin", "pr", "list", "--state", "all", "--head", branch,
                         "--json", "number,status,headRef"], ("status", "headRef")),
                        (["gh", "pr", "list", "--state", "all", "--head", branch,
                          "--json", "number,state,headRefName"], ("state", "headRefName"))]:
        raw = run(cmd, repo)
        if raw is None:
            continue
        try:
            matches = [item for item in json.loads(raw) if item[fields[1]] == branch]
            states = [(str(item["number"]), item[fields[0]].lower()) for item in matches]
        except (TypeError, KeyError, ValueError, AttributeError):
            continue
        for number, state in states:
            if state in ("open", "draft"):
                return f"#{number}/{state}", "open"
        if states:
            number, state = states[0]
            return f"#{number}/{state}", state
        return "-", "none"
    return "?", "unknown"


def inspect(repo, wt, base, activity, origin, locked):
    branch = (git(wt, "symbolic-ref", "--short", "-q", "HEAD") or "").strip()
    changes = git(wt, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    dirty = "unknown" if changes is None else "clean"
    if changes:
        dirty = "scratch" if all(x.startswith("?? ") for x in changes.split("\0") if x) else "wip"
    merged = git(wt, "merge-base", "--is-ancestor", "HEAD", base) is not None
    pr, pr_state = pr_status(repo, branch, origin)
    if locked:
        bucket = "hold-locked"
    elif dirty != "clean":
        bucket = "hold-" + dirty
    elif pr_state == "open":
        bucket = "hold-open-pr"
    elif activity == "active":
        bucket = "verify-recent-chat"
    elif activity == "inactive" and pr_state != "unknown" and merged:
        bucket = "safe"
    else:
        bucket = "review"
    remote = "detached" if not branch else "no-remote"
    if branch and git(wt, "show-ref", "--verify", "--quiet", "refs/remotes/origin/" + branch) is not None:
        counts = git(wt, "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD")
        remote = "pushed" if counts and counts.split() == ["0", "0"] else "diverged"
    timestamp = git(wt, "log", "-1", "--format=%ct")
    age = f"{int((time.time() - int(timestamp)) // 86400)}d" if timestamp else "?"
    size = (run(["du", "-sk", str(wt)], repo) or "?").split()[0]
    return [size, age, "YES" if merged else "no", dirty, remote, pr, activity, bucket, str(wt)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-b", "--base")
    parser.add_argument("--activity", type=Path, help="current project-scoped activity snapshot")
    parser.add_argument("repo", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    inventory = git(args.repo, "worktree", "list", "--porcelain", "-z")
    if inventory is None:
        parser.error("cannot read git worktree list")
    candidates = [args.base] if args.base else ["origin/HEAD", "origin/main", "origin/master"]
    base = next((x for x in candidates if git(args.repo, "rev-parse", "--verify", "--quiet", x + "^{commit}") is not None), None)
    if not base:
        parser.error("cannot resolve base; pass -b <ref>")
    # Use local refs. The caller selects the verified comparison revision.
    head = git(args.repo, "rev-parse", base + "^{commit}").strip()
    activity = activity_file(args.activity)
    remotes = git(args.repo, "remote")
    entries = []
    for record in inventory.strip("\0").split("\0\0"):
        fields = record.split("\0")
        path = Path(fields[0].removeprefix("worktree "))
        locked = any(item.partition(" ")[0] == "locked" for item in fields[1:])
        entries.append((path, locked))
    print(f"# base: {base} ({head})")
    print("SIZE_KIB\tAGE\tMERGED\tDIRTY\tREMOTE\tPR\tACTIVITY\tBUCKET\tWORKTREE")
    rows = [inspect(args.repo, wt, head, activity.get(wt.resolve(), "unknown"), remotes, locked) for wt, locked in entries[1:]]
    for row in sorted(rows, key=lambda r: int(r[0]) if r[0].isdigit() else -1, reverse=True):
        print("\t".join(row))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))
