"""Shared rules for the model-fit review: which messages count, how runs and
episodes are formed. Standard library only.

Data shapes (all JSON-serialisable dicts):

message: {"id", "thread", "at", "text", "run_id", "provider"}
         -- one human message; run_id/provider name the run it is attached
         to (None when unknown). Log-path messages have provider "claude".
run:     {"run_id", "thread", "provider", "initiator", "model", "effort",
          "requested_at", "completed_at", "request", "request_ids",
          "reply_end", "max_context_tokens"}
         -- initiator is "human" (a person's message started it) or "agent"
         (a delegation result, notification or another session started it).
timeline entry: {"run_id", "thread", "provider", "completed_at"}
         -- every completed run of a thread, any provider and initiator.

Times are ISO-8601 UTC strings ("...Z"), so string order equals time order,
and the first 10 characters are the UTC date.

Scripts that write files honor TMPDIR (Python tempfile) and SQLITE_TMPDIR
(SQLite temporary tables); set them to keep temporary files off a small disk.
"""
from __future__ import annotations

import collections
import json
import random
import re
import subprocess
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Iterable

# Session commands are not tasks. "/칟ㅁㄱ" is "/clear" typed on a Korean
# two-set keyboard layout. Any "/reload-..." command is also a session command.
CONTROL = {"/compact", "/clear", "/mcp", "/output-style", "/칟ㅁㄱ",
           "/model", "/effort", "/config", "/resume", "/exit"}
CONTROL_PREFIXES = ("/reload-",)

# T3 Code: only these rows are messages a person typed. "server" rows with
# createdBy="user" are answers to an agent's question prompt; they hold the
# question text and the chosen option, and arrive while the run is going.
# They are counted as `answers`, never as reactions, steer or requests.
T3_HUMAN_SOURCES = ("web", "mobile")
T3_ANSWER_SOURCE = "server"

# Claude Code log entries whose prompt was not typed by a person. Layer 1 is
# the entry's own fields (see prompt_kind); layer 2 is this prefix denylist,
# for injected prompts that carry no marking field. Each pattern is matched
# at the start of the prompt text.
INJECTED_PATTERNS = [re.compile(p) for p in (
    r"Delegated task node:",                       # T3 delegated task brief or result
    r"Act as the [\w-]+ sub-agent",                # delegation brief
    r"Continue where you left off",                # resume after an interruption
    r"Context handoff",                            # thread handoff summary
    r"\[T3 Code: the agent in T3 thread",          # message relayed from another thread
    r"This session is being continued from a previous conversation",  # compact summary
    r"Note: the T3 server restarted",              # server notice
    r"Update on pull request #",                   # PR watch notice
    r"<task-notification>",                        # background task finished
)]

# Harness markers stored as user entries; they start no turn.
NOT_PROMPTS = ("[Request interrupted by user",)

_COMMAND = re.compile(r"<command-name>\s*(/?[^<\s]+)\s*</command-name>")
_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)

FAMILIES = ("haiku", "sonnet", "opus", "fable")

# Model names and ids are masked in every item a classifier or judge reads.
_MODEL_NAMES = re.compile(
    r"(?i)\b(?:claude-[a-z0-9.-]+|gpt-[0-9][a-z0-9.-]*|"
    r"(?:fable|opus|sonnet|haiku|mythos)(?:[ -]?\d+(?:[.-]\d+)*)?)(?![a-z])"
    r"|소넷|오퍼스|오푸스|하이쿠|페이블|미토스")
MODEL_MASK = "[model]"


def model_family(model: str | None) -> str:
    """'claude-opus-5-5' -> 'opus'. Unknown or other vendors -> the raw name or 'unknown'."""
    m = (model or "").lower()
    for fam in FAMILIES:
        if fam in m:
            return fam
    return m or "unknown"


def is_claude_provider(provider: str | None) -> bool:
    return (provider or "").lower().startswith("claude")


def mask_models(text: str | None) -> str:
    return _MODEL_NAMES.sub(MODEL_MASK, text or "")


def is_control(text: str | None) -> bool:
    """True when the message is a session command, not a task request."""
    words = (text or "").strip().split()
    if not words:
        return False
    head = words[0]
    return head in CONTROL or head.startswith(CONTROL_PREFIXES)


def is_t3_human(role: str, payload: dict) -> bool:
    """T3 state DB rule: other role='user' rows are delegation results,
    notices, messages from other sessions and answers to question prompts."""
    return (role == "user" and payload.get("createdBy") == "user"
            and payload.get("creationSource") in T3_HUMAN_SOURCES)


def is_injected(text: str) -> bool:
    return any(p.match(text) for p in INJECTED_PATTERNS)


def _prompt_text(entry: dict) -> str | None:
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in content):
            return None
        parts = [x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text"]
    else:
        return None
    texts = []
    for part in parts:
        s = part.strip()
        if not s:
            continue
        if s.startswith("<"):
            m = _COMMAND.search(s)
            if m:
                name = m.group(1) if m.group(1).startswith("/") else "/" + m.group(1)
                a = _ARGS.search(s)
                s = (name + " " + (a.group(1).strip() if a else "")).strip()
            elif not s.startswith("<task-notification>"):
                continue  # system reminder, command output
        texts.append(s)
    return "\n".join(texts) if texts else None


def prompt_kind(entry: dict) -> tuple[str | None, str | None]:
    """Classify a Claude Code log entry as a prompt.

    Returns ("human", text), ("agent", text) or (None, None).
    - None: not a prompt (assistant entry, tool result, meta, sidechain,
      compact summary, transcript-only entry, system reminder).
    - agent: a prompt that starts a turn but was not typed by a person. Field
      layer: origin.kind other than "human" (peer, task-notification),
      turnOrigin "task_notification" or "peer", promptSource "system".
      Text layer: INJECTED_PATTERNS.
    - human: everything else. Slash commands come back as "/name args".
    """
    if entry.get("type") != "user" or entry.get("isSidechain"):
        return None, None
    if entry.get("isMeta") or entry.get("isCompactSummary") or entry.get("isVisibleInTranscriptOnly"):
        return None, None
    text = _prompt_text(entry)
    if text is None or text.startswith(NOT_PROMPTS):
        return None, None
    origin = entry.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return "agent", text
    if entry.get("turnOrigin") in ("task_notification", "peer") or entry.get("promptSource") == "system":
        return "agent", text
    if is_injected(text):
        return "agent", text
    return "human", text


def log_human_text(entry: dict) -> str | None:
    """Text a person typed for a Claude Code log entry, else None."""
    kind, text = prompt_kind(entry)
    return text if kind == "human" else None


# Attachment markers: "[File: x; ref=…]" / "[Image #1]" in logs, "[x](t3-context://…)" in T3.
# Context blocks such as "<t3_context>…</t3_context>" that the host appends are dropped too.
_ATTACH = re.compile(r"\[(?:File|Image|Attachment)\b[^\]]*\]|\[Attached (?:image|file)\b[^\]]*\]"
                     r"|\[[^\]]*\]\(t3-context://[^)]*\)|<(\w+)[^>]*>[\s\S]*?(?:</\1>|$)", re.I)
_ATTACH_ONLY = "[User attached one or more files without additional text."
_SKILL = re.compile(r"(?<!\S)[$/]([A-Za-z][\w:.-]*)")


def norm_prompt(text: str | None) -> tuple[frozenset, str]:
    """Normalize a prompt for matching T3 messages with log prompts.

    Returns (skill tokens, rest). `$skill` (T3) and `/skill` (log) both become
    the token "skill", wherever they stand in the text. Attachment markers are
    dropped, whitespace runs collapse, and the rest is cut to 200 characters.
    """
    s = (text or "").strip()
    if s.startswith(_ATTACH_ONLY):
        s = ""
    s = _ATTACH.sub(" ", s)
    skills = frozenset(_SKILL.findall(s))
    rest = re.sub(r"\s+", " ", _SKILL.sub(" ", s)).strip()
    return skills, rest[:200]


def ts_seconds(at: str) -> float:
    return datetime.fromisoformat(at.replace("Z", "+00:00")).timestamp()


def prompts_match(log_text: str, t3_text: str, dt: float, tolerance_s: float = 600) -> bool:
    """A log prompt matches a T3 message when the times differ by at most
    tolerance_s, the log's skill tokens all occur in the T3 text, and the
    rests are equal or one contains the other (both at least 8 characters,
    or 4 when the log prompt names a skill).
    A log prompt that is only a slash command (its typed text sits in a
    separate meta entry) matches within 30 seconds."""
    if abs(dt) > tolerance_s:
        return False
    ls, lr = norm_prompt(log_text)
    ts, tr = norm_prompt(t3_text)
    if not ls <= ts:
        return False
    if lr == tr:
        return bool(lr) or abs(dt) <= 30
    if not lr:
        return bool(ls) and abs(dt) <= 30
    shortest = 4 if ls else 8  # a shared skill token already narrows the match
    return min(len(lr), len(tr)) >= shortest and (lr in tr or tr in lr)


def match_prompts(log_msgs: list[dict], t3_msgs: list[dict], tolerance_s: float = 600) -> dict[str, str]:
    """Match log prompts to T3 human messages of the same (mapped) thread.

    Both lists hold {"id", "thread", "at", "text"}; a log message's thread must
    already be the T3 thread id. Pairs must pass prompts_match. Each T3
    message is used once; the nearest in time wins. Returns {log_id: t3_id}.
    """
    by_thread: dict[str, list[dict]] = collections.defaultdict(list)
    for m in t3_msgs:
        by_thread[m["thread"]].append(dict(m, _t=ts_seconds(m["at"])))
    used: set[str] = set()
    out = {}
    for lm in sorted(log_msgs, key=lambda m: m["at"]):
        t = ts_seconds(lm["at"])
        best = None
        for c in by_thread.get(lm["thread"], []):
            if c["id"] in used or not prompts_match(lm["text"], c["text"], c["_t"] - t, tolerance_s):
                continue
            if best is None or abs(c["_t"] - t) < abs(best["_t"] - t):
                best = c
        if best is not None:
            used.add(best["id"])
            out[lm["id"]] = best["id"]
    return out


def timeline_of(runs: list[dict]) -> list[dict]:
    return [{"run_id": r["run_id"], "thread": r["thread"], "provider": r.get("provider"),
             "completed_at": r["completed_at"]} for r in runs if r.get("completed_at")]


def assign_reactions(runs: list[dict], messages: list[dict],
                     timeline: list[dict] | None = None) -> list[dict]:
    """Give each run its reaction, its steer messages and its follow state.

    `timeline` lists every completed run of each thread (any provider, human-
    or agent-initiated); by default it is built from `runs`. For run R:

    - next: the first human message sent at or after R.completed_at
      (R's own request messages excluded).
    - follow_state "reaction": no other run of the thread completed after R
      and at or before `next`, and `next` is not attached to a non-Claude
      run. reaction_id = next.
    - "superseded": another run L completed in between, so `next` reacts to
      a later result. reaction_id = None, superseded_by = L (the latest such
      run). If L is in `runs` (a Claude run), `next` is L's reaction by the
      same rule.
    - "other_provider": `next` is attached to a non-Claude run; it is never
      a reaction to a Claude run.
    - "end": no later human message.
    - steer: human messages sent after R.requested_at and before
      R.completed_at, excluding R's first request and messages attached to a
      non-Claude run. The user had not seen R's result yet.
    """
    tl = timeline if timeline is not None else timeline_of(runs)
    done_by_thread: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for t in tl:
        if t.get("completed_at"):
            done_by_thread[t["thread"]].append((t["completed_at"], t["run_id"]))
    for lst in done_by_thread.values():
        lst.sort()
    by_thread: dict[str, list[dict]] = collections.defaultdict(list)
    for m in messages:
        by_thread[m["thread"]].append(m)
    for lst in by_thread.values():
        lst.sort(key=lambda m: (m["at"], m["id"]))

    def other_provider(m: dict) -> bool:
        p = m.get("provider")
        return p is not None and not is_claude_provider(p)

    out = []
    for r in runs:
        msgs = by_thread.get(r["thread"], [])
        done = r.get("completed_at")
        first = set((r.get("request_ids") or [])[:1])
        steer, nxt = [], None
        for m in msgs:
            if m["id"] in first or m["at"] < r["requested_at"]:
                continue
            if done and m["at"] < done:
                if m["at"] > r["requested_at"] and not other_provider(m):
                    steer.append(m["id"])
                continue
            nxt = m
            break
        row = dict(r, steer_ids=steer, next_id=nxt["id"] if nxt else None,
                   reaction_id=None, superseded_by=None, follow_state="end")
        if nxt is not None:
            later = [rid for at, rid in done_by_thread[r["thread"]]
                     if done and done < at <= nxt["at"] and rid != r["run_id"]]
            if later:
                row.update(follow_state="superseded", superseded_by=later[-1])
            elif other_provider(nxt):
                row["follow_state"] = "other_provider"
            else:
                row.update(follow_state="reaction", reaction_id=nxt["id"])
        out.append(row)
    return out


def in_window(at: str | None, since: str = "", until: str = "") -> bool:
    """`since` and `until` are inclusive UTC dates (YYYY-MM-DD)."""
    d = (at or "")[:10]
    return bool(d) and (not since or d >= since) and (not until or d <= until)


def apply_window(messages: list[dict], runs: list[dict], since: str = "", until: str = ""
                 ) -> tuple[list[dict], list[dict]]:
    """Keep runs whose first request time is in the window, the messages in
    the window, and the messages those runs refer to (so a reaction sent
    after `until` still resolves). Apply after assign_reactions."""
    if not since and not until:
        return messages, runs
    runs_w = [r for r in runs if in_window(r["requested_at"], since, until)]
    ref = set()
    for r in runs_w:
        ref.update(r.get("request_ids") or [])
        ref.update(r.get("steer_ids") or [])
        ref.update(i for i in (r.get("reaction_id"), r.get("next_id")) if i)
    msgs_w = [m for m in messages if in_window(m["at"], since, until) or m["id"] in ref]
    return msgs_w, runs_w


def summary(messages: list[dict], runs: list[dict], since: str = "", until: str = "",
            answers: int | None = None) -> list[str]:
    """Count lines with the same denominators on both paths. `messages` and
    `runs` are the windowed lists; window counts use the message time."""
    w = [m for m in messages if in_window(m["at"], since, until)] if (since or until) else messages
    on_claude = sum(1 for m in w if m.get("provider") is None or is_claude_provider(m.get("provider")))
    human = [r for r in runs if r.get("initiator") == "human"]
    states = collections.Counter(r["follow_state"] for r in runs)
    window = f"{since or '…'}..{until or '…'} UTC" if (since or until) else "all time"
    lines = [f"window {window}",
             f"human messages {len(w)}  attached to Claude runs or unattached {on_claude}"
             + (f"  question answers (not counted) {answers}" if answers is not None else ""),
             f"Claude runs {len(runs)}  human-initiated {len(human)}  agent-initiated {len(runs) - len(human)}",
             "follow states " + "  ".join(f"{k} {states.get(k, 0)}" for k in
                                         ("reaction", "superseded", "other_provider", "end")),
             f"steer messages {sum(len(r['steer_ids']) for r in runs)}",
             f"effort known {sum(1 for r in human if r.get('effort'))}/{len(human)} human-initiated runs"]
    return lines


def write_check_sample(out_dir, messages: list[dict], since: str = "", until: str = "",
                       n: int = 10, seed: int = 7) -> tuple[Path, int]:
    """Write n random human messages of the window (fixed seed) to
    human_check.jsonl for the Phase B precision check: read each row and count
    the ones a person typed. Returns (path, rows written)."""
    pool = [m for m in messages if in_window(m["at"], since, until)] if (since or until) else messages
    rows = [{"id": m["id"], "at": m["at"], "text": m["text"][:300], "typed_by_person": None}
            for m in random.Random(seed).sample(pool, min(n, len(pool)))]
    path = Path(out_dir) / "human_check.jsonl"
    write_jsonl(path, rows)
    return path, len(rows)


def reaction_items(runs: list[dict], texts: dict[str, str]) -> list[tuple[dict, str, str]]:
    """(run, message_id, kind) for every item to label. Runs whose request is a
    session command are skipped; so are session-command reactions."""
    out = []
    for r in runs:
        if is_control(r["request"]):
            continue
        rid = r.get("reaction_id")
        if r.get("follow_state") == "reaction" and rid and not is_control(texts.get(rid)):
            out.append((r, rid, "reaction"))
        out += [(r, s, "steer") for s in r.get("steer_ids", [])]
    return out


def follow_label(run: dict, labels: dict[str, str], texts: dict[str, str]) -> str:
    """Label of the run's reaction: a classifier label, or end / session /
    superseded / other_provider / unlabeled."""
    if run["follow_state"] != "reaction":
        return run["follow_state"]
    rid = run["reaction_id"]
    if is_control(texts.get(rid)):
        return "session"
    return labels.get(rid, "unlabeled")


def group_episodes(runs: list[dict], labels: dict[str, str], texts: dict[str, str],
                   steer_labels: dict[str, str] | None = None,
                   exclude_threads: Iterable[str] = ()) -> list[dict]:
    """Episodes start at the first run of a thread or after a `new_topic`
    reaction. Control runs take part in the boundaries but are not task runs.
    Agent-initiated runs are task runs (they did work the user saw) and are
    counted in n_agent_runs; model and effort come from human-initiated runs
    when there are any. An episode whose runs are all agent-initiated (a
    delegated child session) has delegated=True. `labels` holds reaction labels, `steer_labels` steer
    labels, both keyed by message id."""
    steer_labels = steer_labels or {}
    skip = set(exclude_threads)
    ordered = sorted((r for r in runs if r["thread"] not in skip),
                     key=lambda r: (r["thread"], r["requested_at"], r["run_id"]))
    episodes: list[dict] = []
    cur, prev_thread, prev_label = None, None, None
    for r in ordered:
        if r["thread"] != prev_thread or prev_label == "new_topic":
            cur = {"episode": f"e{len(episodes):04d}", "thread": r["thread"], "runs": []}
            episodes.append(cur)
        lab = follow_label(r, labels, texts)
        cur["runs"].append(dict(r, follow=lab,
                                steer=[steer_labels.get(i, "unlabeled") for i in r["steer_ids"]],
                                control=is_control(r["request"])))
        prev_thread, prev_label = r["thread"], lab

    out = []
    for ep in episodes:
        task = [r for r in ep["runs"] if not r["control"]]
        if not task:
            continue
        human = [r for r in task if r.get("initiator", "human") == "human"]
        n_agent = len(task) - len(human)
        human = human or task
        c = collections.Counter(r["follow"] for r in task)
        steer = collections.Counter(s for r in task for s in r["steer"])
        mc = collections.Counter((r.get("model") or "unknown", r.get("effort") or "unknown") for r in human)
        (model, effort), _ = mc.most_common(1)[0]
        out.append({
            "episode": ep["episode"], "thread": ep["thread"],
            "start": task[0]["requested_at"], "end": task[-1]["requested_at"],
            "n_runs": len(task), "n_agent_runs": n_agent, "delegated": n_agent == len(task),
            "model": model, "effort": effort,
            "mixed_models": len({r.get("model") for r in task}) > 1,
            "fix": c["fix"], "method": c["method"], "clarify": c["clarify"],
            "extend": c["extend"], "superseded": c["superseded"], "other_provider": c["other_provider"],
            "steer_correct": steer["correct"], "steer_method": steer["method"],
            "outcome": "smooth" if c["fix"] == 0 else ("rough" if c["fix"] >= 2 else "one_fix"),
            "first_request": (human[0]["request"] or "")[:400],
            "run_ids": [r["run_id"] for r in task],
        })
    return out


def sample(items: list, k: int, seed: int) -> list:
    """A random sample of k items (all if fewer), stable for a seed, in input order."""
    if k >= len(items):
        return list(items)
    idx = sorted(random.Random(seed).sample(range(len(items)), k))
    return [items[i] for i in idx]


def ro_uri(path, immutable: bool = False) -> str:
    """SQLite read-only URI with the path percent-encoded ('?', '#', '%' and
    spaces in a path would otherwise break the URI)."""
    q = urllib.parse.quote(str(Path(path).expanduser().resolve()))
    return f"file:{q}?mode=ro" + ("&immutable=1" if immutable else "")


def check_output_dir(path, allow_repo: bool = False) -> str | None:
    """Refuse an output directory inside a git work tree unless git ignores
    it: review files hold message text and must not be committed by mistake.
    Returns an error message, or None when the directory is fine."""
    if allow_repo:
        return None
    p = Path(path).expanduser().resolve()
    probe = p
    while not probe.exists():
        probe = probe.parent
    try:
        top = subprocess.run(["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None  # no git: nothing to protect
    if top.returncode != 0:
        return None
    ignored = subprocess.run(["git", "-C", top.stdout.strip(), "check-ignore", "-q", str(p) + "/"],
                             capture_output=True, timeout=20)
    if ignored.returncode == 0:
        return None
    return (f"{p} is inside the git work tree {top.stdout.strip()} and is not git-ignored; "
            "choose a directory outside any repository, add it to .gitignore, or pass --allow-repo")


def read_jsonl(path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows: Iterable[dict]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n
