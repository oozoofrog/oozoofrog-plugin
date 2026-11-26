#!/usr/bin/env python3
"""Turn edited copies of pull request files into GitHub suggestion comments.

The base text of every file comes from the git object at --head, so each
suggestion is anchored to the pull request head. Every comment range must lie
inside one hunk of the pull request diff (--base...--head, renames detected,
3 lines of context), because GitHub
rejects the whole review otherwise. Before writing anything, the script applies
its own suggestions to the base text and requires the result to equal the
edited copy. Lines are split on "\\n" only, as GitHub does.

Usage:
  suggest.py --repo REPO --base BASE --head SHA --proposed DIR --body BODY.md
             [--notes NOTES.json] [--gap N] [--diff-out FILE]
             [--format gh | --format t3 --repository OWNER/REPO --number N]

DIR mirrors repository-relative paths and holds only the files you changed.
NOTES.json maps "path:start-end" (as printed on stderr) to a short reason that
is put above that suggestion.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

T3_COMMENT_LIMIT = 50
SKIPPED_NAMES = {".DS_Store"}
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


def fail(message: str) -> None:
    sys.exit(f"suggest.py: {message}")


def git(repo: str, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if result.returncode != 0:
        raise LookupError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def decode(data: bytes, label: str) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail(f"{label} is not UTF-8 text")
    if "\r" in text:
        fail(f"{label} contains CR line endings; describe this change in the review body instead")
    return text


def pr_hunks(repo: str, base: str, head: str) -> dict[str, list[tuple[int, int]]]:
    """Map each head-side path to the 1-based inclusive line ranges that the PR diff shows.

    The diff covers the whole PR so renames are detected. Diff settings are pinned
    to match GitHub's "Files changed" view: 3 lines of context, and hunks one line
    apart are joined (checked against 476 files from 18 pull requests).
    """
    out = git(repo, "-c", "diff.interHunkContext=1", "-c", "diff.noprefix=false", "-c", "core.quotePath=false",
              "diff", "--no-color", "--no-ext-diff", "--no-textconv", "--diff-algorithm=myers", "-M",
              "--unified=3", "--src-prefix=a/", "--dst-prefix=b/", f"{base}...{head}")
    hunks: dict[str, list[tuple[int, int]]] = {}
    current = None
    for line in out.decode("utf-8", "replace").split("\n"):
        if line.startswith("diff --git "):
            current = None
        elif line.startswith("+++ "):
            target = line[4:].rstrip("\t")
            current = hunks.setdefault(target[2:], []) if target.startswith("b/") else None
        elif current is not None and (match := HUNK.match(line)):
            start, count = int(match.group(1)), int(match.group(2) or 1)
            if count:
                current.append((start, start + count - 1))
    return hunks


def changed_ranges(base: list[str], new: list[str], gap: int) -> list[tuple[int, int, list[str]]]:
    """Return (start, end, replacement) with 0-based, end-exclusive base ranges."""
    ops = [op for op in difflib.SequenceMatcher(None, base, new, autojunk=False).get_opcodes() if op[0] != "equal"]
    groups: list[list[int]] = []
    for _, i1, i2, j1, j2 in ops:
        if groups and i1 - groups[-1][1] <= gap:
            groups[-1][1], groups[-1][3] = i2, j2
        else:
            groups.append([i1, i2, j1, j2])
    ranges = []
    for i1, i2, j1, j2 in groups:
        lines = new[j1:j2]
        if i1 == i2:  # pure insertion: GitHub needs at least one existing line
            if not base:
                fail("an empty file has no line to attach a suggestion to")
            if i1 > 0:
                i1, lines = i1 - 1, [base[i1 - 1]] + lines
            else:
                i2, lines = 1, lines + [base[0]]
        if ranges and i1 < ranges[-1][1]:
            fail("two suggestions would cover the same line; raise --gap")
        ranges.append((i1, i2, lines))
    return ranges


def replay(base: list[str], ranges: list[tuple[int, int, list[str]]]) -> list[str]:
    result = list(base)
    for start, end, lines in sorted(ranges, reverse=True):
        result[start:end] = lines
    return result


def split_lines(text: str) -> list[str]:
    lines = text.split("\n")
    return lines[:-1] if text.endswith("\n") else lines


def suggestion_block(lines: list[str]) -> str:
    longest = max((len(run) for line in lines for run in re.findall(r"`+", line)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}suggestion\n" + "".join(f"{line}\n" for line in lines) + fence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base", required=True, help="base branch commit; the PR diff is BASE...HEAD")
    parser.add_argument("--head", required=True)
    parser.add_argument("--proposed", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--notes")
    parser.add_argument("--gap", type=int, default=2, help="merge changes separated by at most N unchanged lines (N >= 1)")
    parser.add_argument("--format", choices=("t3", "gh"), default="gh")
    parser.add_argument("--repository", help="OWNER/REPO, required with --format t3")
    parser.add_argument("--number", type=int, help="pull request number, required with --format t3")
    parser.add_argument("--diff-out")
    args = parser.parse_args()
    if args.gap < 1:
        parser.error("--gap must be 1 or more")
    if args.format == "t3" and not (args.repository and args.number):
        parser.error("--format t3 needs --repository and --number")

    proposed_root = Path(args.proposed)
    files = sorted(p for p in proposed_root.rglob("*") if p.is_file() and p.name not in SKIPPED_NAMES)
    if not files:
        fail(f"no files under {proposed_root}")
    notes = json.loads(Path(args.notes).read_text(encoding="utf-8")) if args.notes else {}
    try:
        all_hunks = pr_hunks(args.repo, args.base, args.head)
    except LookupError as error:
        fail(f"cannot diff {args.base}...{args.head}: {error}")

    comments, diff_parts, problems = [], [], []
    added = removed = touched = 0
    for file in files:
        path = file.relative_to(proposed_root).as_posix()
        try:
            old_bytes = git(args.repo, "show", f"{args.head}:{path}")
        except LookupError:
            fail(f"{path} does not exist at {args.head}; a new file cannot be a suggestion")
        old_text = decode(old_bytes, f"{path} at head")
        new_text = decode(file.read_bytes(), f"{path} (edited copy)")
        if old_text == new_text:
            continue
        if old_text.endswith("\n") != new_text.endswith("\n"):
            fail(f"{path}: a change to the final newline cannot be a suggestion")
        base, new = split_lines(old_text), split_lines(new_text)
        ranges = changed_ranges(base, new, args.gap)
        if replay(base, ranges) != new:
            fail(f"{path}: suggestions do not reproduce the edited file")
        hunks = all_hunks.get(path, [])
        touched += 1
        diff = list(difflib.unified_diff(base, new, f"a/{path}", f"b/{path}", lineterm=""))
        added += sum(1 for line in diff[2:] if line.startswith("+"))
        removed += sum(1 for line in diff[2:] if line.startswith("-"))
        diff_parts.append("\n".join(diff) + "\n")
        for start, end, lines in ranges:
            key = f"{path}:{start + 1}-{end}"
            if not any(low <= start + 1 and end <= high for low, high in hunks):
                problems.append(key)
                continue
            note = notes.pop(key, "").strip()
            body = (f"{note}\n\n" if note else "") + suggestion_block(lines)
            if args.format == "t3":
                comment = {"path": path, "line": end, "side": "new", "body": body}
                if end > start + 1:
                    comment["startLine"] = start + 1
            else:
                comment = {"path": path, "line": end, "side": "RIGHT", "body": body}
                if end > start + 1:
                    comment["start_line"], comment["start_side"] = start + 1, "RIGHT"
            comments.append(comment)
            print(key, file=sys.stderr)

    if problems:
        fail("outside one hunk of the pull request diff (lower --gap, or describe these in the body): "
             + ", ".join(problems))
    if notes:
        fail(f"unused notes keys: {sorted(notes)}")
    if not comments:
        fail("the edited files match the pull request head")
    if args.format == "t3" and len(comments) > T3_COMMENT_LIMIT:
        fail(f"{len(comments)} comments exceed the T3 review limit of {T3_COMMENT_LIMIT}")
    if args.diff_out:
        Path(args.diff_out).write_text("".join(diff_parts), encoding="utf-8")

    body = Path(args.body).read_text(encoding="utf-8").strip()
    if args.format == "t3":
        review = {"repository": args.repository, "number": args.number, "verdict": "comment",
                  "expectedHeadSha": args.head, "body": body, "comments": comments}
    else:
        review = {"commit_id": args.head, "event": "COMMENT", "body": body, "comments": comments}
    json.dump(review, sys.stdout, ensure_ascii=False, indent=2)
    print()
    print(f"{touched} files, {len(comments)} suggestions, +{added}/-{removed} lines", file=sys.stderr)


if __name__ == "__main__":
    main()
