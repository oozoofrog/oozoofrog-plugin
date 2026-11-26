#!/usr/bin/env bash
# Builds a tiny local git repository in the current directory (the run's empty workspace).
# Writes only below "$PWD". Makes no network calls. Has no remote.
# Options: --with-plan  add docs/plan and docs/decisions files with open work.
#          --with-diff  leave one uncommitted change in pager.py.
#          --with-wiki  add a git-ignored project-wiki vault in _context/wiki.
set -euo pipefail

with_plan=0
with_diff=0
with_wiki=0
for arg in "$@"; do
  case "$arg" in
    --with-plan) with_plan=1 ;;
    --with-diff) with_diff=1 ;;
    --with-wiki) with_wiki=1 ;;
    *) echo "unknown option: $arg" >&2; exit 64 ;;
  esac
done

# Every git call disables hooks, fsmonitor helpers and signing.
git_safe() {
  git -c core.hooksPath=/dev/null -c core.fsmonitor= -c commit.gpgsign=false -c tag.gpgsign=false "$@"
}

refuse() {
  echo "pager-repo.sh: refusing to run in $PWD: $1" >&2
  echo "pager-repo.sh: run it only in a new empty directory outside any git work tree." >&2
  exit 65
}

if [ -n "$(find . -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  refuse "the directory is not empty"
fi

# `claude plugin eval` runs the scaffold in <run>/home/cwd and places an empty sentinel repository
# (no commits) at <run>/home/.git, with HOME=<run>/home. Only that exact layout is allowed.
if top=$(git_safe rev-parse --show-toplevel 2>/dev/null); then
  home_real=$(cd "$HOME" 2>/dev/null && pwd -P) || refuse "the directory is inside a git work tree ($top)"
  if [ "$top" != "$home_real" ] || [ "$(pwd -P)" != "$home_real/cwd" ] \
     || git_safe rev-parse -q --verify HEAD >/dev/null 2>&1; then
    refuse "the directory is inside a git work tree ($top)"
  fi
fi

mkdir -p tests

cat > pager.py <<'PY'
"""Split a sequence into pages. Pages are numbered from 1."""
import argparse
import sys


def paginate(items, page, size):
    """Return page `page` (1-based) of `items`, with `size` items per page."""
    if page < 1 or size < 1:
        raise ValueError("page and size must be >= 1")
    start = page * size
    return list(items[start:start + size])


def page_count(total, size):
    """Return how many pages `total` items fill at `size` items per page."""
    return (total + size - 1) // size


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print one page of lines from a text file.")
    parser.add_argument("path")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--size", type=int, default=10)
    args = parser.parse_args(argv)
    with open(args.path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    for line in paginate(lines, args.page, args.size):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
PY

cat > report.py <<'PY'
"""Summarize a CSV of page views per document."""
import csv


class ReportBuilder:
    def __init__(self, source_path, output_path):
        self.source_path = source_path
        self.output_path = output_path
        self.rows = []
        self.totals = {}

    def run(self):
        with open(self.source_path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                self.rows.append({"doc": row["doc"].strip(), "views": int(row["views"])})
        for row in self.rows:
            self.totals[row["doc"]] = self.totals.get(row["doc"], 0) + row["views"]
        ranked = sorted(self.totals.items(), key=lambda item: (-item[1], item[0]))
        lines = ["doc,views"] + [f"{doc},{views}" for doc, views in ranked]
        with open(self.output_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return ranked
PY

: > tests/__init__.py
cat > tests/test_pages.py <<'PY'
import unittest

from pager import page_count, paginate


class PageCountTests(unittest.TestCase):
    def test_partial_last_page_is_counted(self):
        self.assertEqual(page_count(10, 3), 4)

    def test_exact_fit(self):
        self.assertEqual(page_count(9, 3), 3)


class PaginateTests(unittest.TestCase):
    def test_page_size_is_respected(self):
        self.assertEqual(len(paginate(list(range(10)), 1, 3)), 3)

    def test_rejects_page_zero(self):
        with self.assertRaises(ValueError):
            paginate([1, 2, 3], 0, 1)


if __name__ == "__main__":
    unittest.main()
PY

cat > README.md <<'MD'
# pager

Pagnation helper for text files. Pages are numbered from 1.

```sh
python3 pager.py notes.txt --page 2 --size 20
python3 -m unittest
```
MD

if [ "$with_plan" -eq 1 ]; then
  mkdir -p docs/plan docs/decisions
  cat > docs/plan/pagination.md <<'MD'
# Plan: pagination

| Unit | Depends on | Files | Change | Verification IDs | Live check | Status |
|---|---|---|---|---|---|---|
| U1 | — | pager.py | paginate() returns one page | AC-1.1 | `python3 pager.py notes.txt --page 1 --size 3` | done (2026-11-02) |
| U2 | U1 | pager.py | page_count() for a partial last page | AC-1.2 | `python3 -m unittest` | done (2026-11-03) |
| U3 | U1 | pager.py | `--page` past the end prints a clear error | AC-1.3 | `python3 pager.py notes.txt --page 99` | todo |
| U4 | U3 | README.md | Document paging flags | AC-1.4 | read README.md | todo |
MD
  cat > docs/decisions/pending.md <<'MD'
# Decisions

| ID | Decision | Status | Source |
|---|---|---|---|
| D1 | Pages are numbered from 1 | Approved (user, 2026-11-01) | kickoff |
| D2 | `--page` past the end exits with code 2 instead of printing nothing | Proposed (AI) | U3 analysis |
| D3 | Default page size stays 10 | Proposed (AI) | CLI review |
MD
fi

if [ "$with_wiki" -eq 1 ]; then
  printf '_context/\n' > .gitignore
  mkdir -p "_context/wiki/.wiki" "_context/wiki/10 작업 기록" "_context/wiki/20 교훈" "_context/wiki/90 템플릿"
  cat > "_context/wiki/.wiki/config.json" <<'JSON'
{
  "schema_version": 1,
  "kind": "project",
  "lang": "ko",
  "project": "pager",
  "folders": {"episodes": "10 작업 기록", "lessons": "20 교훈", "templates": "90 템플릿"}
}
JSON
  cat > "_context/wiki/90 템플릿/작업 기록 템플릿.md" <<'MD'
---
type: episode
date: {{date}}
request: ""
outcome: in-progress  # success | partial | failure | in-progress
mode: main-session  # main-session | delegated | mixed
lessons: []
evidence: []
---

# {{title}}

## 요청 원문

## 목표와 완료 기준

## 한 일

## 결과

## 회고: 지시

## 회고: 대응

## 근거
MD
  cat > "_context/wiki/20 교훈/버그는 고치기 전에 재현한다.md" <<'MD'
---
type: lesson
audience: agent
kind: response
status: candidate
basis: failure
first_seen: 2026-11-01
last_seen: 2026-11-01
applied: 1
worked: 1
encoded_in: ""
episodes: []
---

# 버그는 고치기 전에 재현한다

> [!abstract] 한 문장
> 버그 보고를 받으면 코드를 고치기 전에 실패하는 실행을 먼저 보인다.

## 적용 기록
| 날짜 | 작업 기록 | 효과 | 내용 |
|---|---|---|---|
| 2026-11-01 | 첫 기록 | 있음 | 재현으로 원인을 바로 찾음 |
MD
fi

git_safe -c init.defaultBranch=main init -q
git_safe add -A
git_safe -c user.name=eval -c user.email=eval@example.invalid commit -q -m "Initial pager"

if [ "$with_diff" -eq 1 ]; then
  cat > pager.py.new <<'PY'
"""Split a sequence into pages. Pages are numbered from 1."""
import argparse
import sys

DEFAULT_SIZE = 25
PY
  sed -n '4,$p' pager.py | sed 's/default=10)/default=DEFAULT_SIZE)/' >> pager.py.new
  mv pager.py.new pager.py
fi
