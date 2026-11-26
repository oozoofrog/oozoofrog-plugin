#!/usr/bin/env bash
# Builds a tiny local git repository in the current directory (the run's empty workspace).
# Writes only below "$PWD". Makes no network calls. Has no remote.
# Options: --with-vault   create the project-wiki vault in _context/wiki with the skill's own wiki_init.py,
#                         plus one episode and one lesson.
#          --broken-link  (with --with-vault) the episode links to a note that does not exist.
set -euo pipefail

with_vault=0
broken_link=0
for arg in "$@"; do
  case "$arg" in
    --with-vault) with_vault=1 ;;
    --broken-link) broken_link=1 ;;
    *) echo "unknown option: $arg" >&2; exit 64 ;;
  esac
done

git_safe() {
  git -c core.hooksPath=/dev/null -c core.fsmonitor= -c commit.gpgsign=false -c tag.gpgsign=false "$@"
}

refuse() {
  echo "wiki-repo.sh: refusing to run in $PWD: $1" >&2
  echo "wiki-repo.sh: run it only in a new empty directory outside any git work tree." >&2
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

cat > pager.py <<'PY'
"""Split a sequence into pages. Pages are numbered from 1."""


def paginate(items, page, size):
    """Return page `page` (1-based) of `items`, with `size` items per page."""
    if page < 1 or size < 1:
        raise ValueError("page and size must be positive")
    start = (page - 1) * size
    return items[start:start + size]
PY

cat > README.md <<'MD'
# pager

`paginate(items, page, size)` returns one page of a list.
MD

printf '_context/\n' > .gitignore

git_safe -c init.defaultBranch=main init -q
git_safe add -A
git_safe -c user.name=eval -c user.email=eval@example.invalid commit -q -m "Initial pager"

if [ "$with_vault" -eq 1 ]; then
  scripts="$(cd "$(dirname "$0")/../../skills/project-wiki/scripts" && pwd)"
  python3 -I -B "$scripts/wiki_init.py" --project "$PWD" --name pager >/dev/null
  vault="$PWD/_context/wiki"
  link="버그는 고치기 전에 재현한다"
  if [ "$broken_link" -eq 1 ]; then
    link="없는 교훈"
  fi
  cat > "$vault/10 작업 기록/2026-11-20 페이지 경계 수정.md" <<MD
---
type: episode
date: 2026-11-20
request: "2페이지 첫 줄이 빠져요"
outcome: success
mode: main-session
lessons:
  - "[[버그는 고치기 전에 재현한다]]"
---

# 페이지 경계 수정

## 요청 원문
2페이지 첫 줄이 빠져요

## 결과
시작 위치 계산을 고쳤다. 관련 교훈: [[$link]]
MD
  cat > "$vault/20 교훈/버그는 고치기 전에 재현한다.md" <<'MD'
---
type: lesson
audience: agent
kind: process
status: candidate
basis: success
first_seen: 2026-11-20
last_seen: 2026-11-20
applied: 1
worked: 1
encoded_in: ""
episodes:
  - "[[2026-11-20 페이지 경계 수정]]"
---

# 버그는 고치기 전에 재현한다

> [!abstract] 한 문장
> 버그 보고를 받으면 코드를 고치기 전에 실패하는 실행을 먼저 보인다.

## 적용 기록
| 날짜 | 작업 기록 | 효과 | 내용 |
|---|---|---|---|
| 2026-11-20 | [[2026-11-20 페이지 경계 수정]] | 있음 | 재현으로 원인을 바로 찾음 |
MD
fi
