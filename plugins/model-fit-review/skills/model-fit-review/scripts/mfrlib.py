"""Shared rules for the model-fit review: which messages count, how runs and
episodes are formed. Standard library only.

Data shapes (all JSON-serialisable dicts):

message: {"id", "thread", "at", "text"}  -- one human message
run:     {"run_id", "thread", "model", "effort", "requested_at", "completed_at",
          "request", "request_ids", "reply_end", "max_context_tokens"}

Times are ISO-8601 strings in one time zone, so string order equals time order.
"""
from __future__ import annotations

import collections
import json
import re
from typing import Iterable

# Session commands are not tasks. "/칟ㅁㄱ" is "/clear" typed on a Korean
# two-set keyboard layout. Any "/reload-..." command is also a session command.
CONTROL = {"/compact", "/clear", "/mcp", "/output-style", "/칟ㅁㄱ",
           "/model", "/effort", "/config", "/resume", "/exit"}
CONTROL_PREFIXES = ("/reload-",)

# T3 Code: only these rows are messages a person typed.
T3_HUMAN_SOURCES = ("web", "mobile")

_COMMAND = re.compile(r"<command-name>\s*(/?[^<\s]+)\s*</command-name>")
_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)


FAMILIES = ("haiku", "sonnet", "opus", "fable")


def model_family(model: str | None) -> str:
    """'claude-opus-5-5' -> 'opus'. Unknown or other vendors -> the raw name or 'unknown'."""
    m = (model or "").lower()
    for fam in FAMILIES:
        if fam in m:
            return fam
    return m or "unknown"


def is_control(text: str | None) -> bool:
    """True when the message is a session command, not a task request."""
    words = (text or "").strip().split()
    if not words:
        return False
    head = words[0]
    return head in CONTROL or head.startswith(CONTROL_PREFIXES)


def is_t3_human(role: str, payload: dict) -> bool:
    """T3 state DB rule: other role='user' rows are delegation results,
    notices and messages from other sessions."""
    return (role == "user" and payload.get("createdBy") == "user"
            and payload.get("creationSource") in T3_HUMAN_SOURCES)


def log_human_text(entry: dict) -> str | None:
    """Return the text a person typed for a Claude Code log entry, else None.

    Skips tool results, meta and sidechain (subagent) entries, and
    system-injected text (anything that starts with '<' except a slash command
    wrapper, which is turned back into '/name args').
    """
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in content):
            return None
        parts = [x.get("text", "") for x in content
                 if isinstance(x, dict) and x.get("type") == "text"]
    else:
        return None
    texts = []
    for part in parts:
        s = part.strip()
        if not s:
            continue
        if s.startswith("<"):
            m = _COMMAND.search(s)
            if not m:
                continue  # system reminder, command output, notification
            name = m.group(1) if m.group(1).startswith("/") else "/" + m.group(1)
            a = _ARGS.search(s)
            s = (name + " " + (a.group(1).strip() if a else "")).strip()
        texts.append(s)
    return "\n".join(texts) if texts else None


def assign_reactions(runs: list[dict], messages: list[dict]) -> list[dict]:
    """Give each run its reaction message and its steer messages.

    - reaction: the first human message in the thread sent at or after the
      run's completed_at, unless another run of the thread completed before
      that message (then the user reacted to the later result) -> None with
      follow_state 'pre_result'.
    - steer: human messages sent after the run's first request and before its
      completed_at, excluding the run's own first request.
    The same run_id listed twice (one row per attached message) is merged first.
    """
    merged: "collections.OrderedDict[str, dict]" = collections.OrderedDict()
    for r in runs:
        cur = merged.get(r["run_id"])
        if cur is None:
            merged[r["run_id"]] = dict(r, request_ids=list(r.get("request_ids") or []))
            continue
        cur["request_ids"] += [i for i in r.get("request_ids") or [] if i not in cur["request_ids"]]
        if r["requested_at"] < cur["requested_at"]:
            cur["requested_at"], cur["request"] = r["requested_at"], r["request"]
    by_thread: dict[str, list[dict]] = collections.defaultdict(list)
    for m in messages:
        by_thread[m["thread"]].append(m)
    for lst in by_thread.values():
        lst.sort(key=lambda m: (m["at"], m["id"]))
    done_by_thread: dict[str, list[str]] = collections.defaultdict(list)
    for r in merged.values():
        if r.get("completed_at"):
            done_by_thread[r["thread"]].append(r["completed_at"])

    out = []
    for r in merged.values():
        msgs = by_thread.get(r["thread"], [])
        done = r.get("completed_at")
        first_ids = set(r["request_ids"][:1])
        steer, reaction, state = [], None, "end"
        for m in msgs:
            if m["at"] <= r["requested_at"] or m["id"] in first_ids:
                continue
            if done and m["at"] < done:
                steer.append(m["id"])
                continue
            later = [d for d in done_by_thread[r["thread"]] if done and done < d <= m["at"]]
            if later:
                state = "pre_result"
            else:
                reaction, state = m["id"], "reaction"
            break
        out.append(dict(r, reaction_id=reaction, follow_state=state, steer_ids=steer))
    return out


def follow_label(run: dict, labels: dict[str, str], texts: dict[str, str]) -> str:
    """Label of the run's reaction: a classifier label, or end / session /
    pre_result / unlabeled."""
    if run["follow_state"] != "reaction":
        return run["follow_state"]
    rid = run["reaction_id"]
    if is_control(texts.get(rid)):
        return "session"
    return labels.get(rid, "unlabeled")


def group_episodes(runs: list[dict], labels: dict[str, str], texts: dict[str, str]) -> list[dict]:
    """Episodes start at the first run of a thread or after a `new_topic`
    reaction. Control runs take part in the boundaries but are not task runs."""
    ordered = sorted(runs, key=lambda r: (r["thread"], r["requested_at"], r["run_id"]))
    episodes: list[dict] = []
    cur, prev_thread, prev_label = None, None, None
    for r in ordered:
        if r["thread"] != prev_thread or prev_label == "new_topic":
            cur = {"episode": f"e{len(episodes):04d}", "thread": r["thread"], "runs": []}
            episodes.append(cur)
        lab = follow_label(r, labels, texts)
        cur["runs"].append(dict(r, follow=lab,
                                steer=[labels.get(i, "unlabeled") for i in r["steer_ids"]],
                                control=is_control(r["request"])))
        prev_thread, prev_label = r["thread"], lab

    out = []
    for ep in episodes:
        task = [r for r in ep["runs"] if not r["control"]]
        if not task:
            continue
        c = collections.Counter(r["follow"] for r in task)
        steer = collections.Counter(s for r in task for s in r["steer"])
        mc = collections.Counter((r.get("model") or "unknown", r.get("effort") or "unknown") for r in task)
        (model, effort), _ = mc.most_common(1)[0]
        out.append({
            "episode": ep["episode"], "thread": ep["thread"],
            "start": task[0]["requested_at"], "end": task[-1]["requested_at"],
            "n_runs": len(task), "model": model, "effort": effort,
            "mixed_models": len({r.get("model") for r in task}) > 1,
            "fix": c["fix"], "method": c["method"], "clarify": c["clarify"],
            "extend": c["extend"], "pre_result": c["pre_result"],
            "steer_fix": steer["fix"], "steer_method": steer["method"],
            "outcome": "smooth" if c["fix"] == 0 else ("rough" if c["fix"] >= 2 else "one_fix"),
            "first_request": (task[0]["request"] or "")[:400],
            "run_ids": [r["run_id"] for r in task],
        })
    return out


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
