"""Tests for the model-fit-review scripts on small synthetic fixtures.
Run: python3 -I -B -m unittest discover -s <skill>/tests -v
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import episodes  # noqa: E402
import export_items  # noqa: E402
import extract_logs  # noqa: E402
import extract_t3  # noqa: E402
import mfrlib  # noqa: E402
import score_practice  # noqa: E402

SCHEMA = """
create table orchestration_v2_projection_runs (run_id text primary key, thread_id text, ordinal integer,
  provider text, status text, requested_at text, completed_at text, payload_json text);
create table orchestration_v2_projection_messages (message_id text primary key, thread_id text, run_id text,
  role text, created_at text, payload_json text);
"""


def msg(mid, thread, run, at, text, role="user", by="user", source="web"):
    payload = {"text": text}
    if role == "user":
        payload.update(createdBy=by, creationSource=source)
    return (mid, thread, run, role, at, json.dumps(payload))


def run(rid, thread, done, model="claude-opus-5-5", effort="medium", status="completed", provider="claudeAgent"):
    payload = {"modelSelection": {"model": model, "options": [{"id": "effort", "value": effort}]}}
    return (rid, thread, 1, provider, status, done, done, json.dumps(payload))


class T3Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db = self.tmp / "snap.sqlite"
        db = sqlite3.connect(self.db)
        db.executescript(SCHEMA)
        db.executemany("insert into orchestration_v2_projection_runs values (?,?,?,?,?,?,?,?)", [
            run("r1", "th", "2026-01-01T10:10"),
            run("r2", "th", "2026-01-01T10:30", model="claude-fable-5-2", effort="high"),
            run("r3", "th", "2026-01-01T10:50"),
            run("rx", "th", "2026-01-01T11:00", provider="codex"),
        ])
        db.executemany("insert into orchestration_v2_projection_messages values (?,?,?,?,?,?)", [
            msg("m1", "th", "r1", "2026-01-01T10:00", "Plan the sync feature"),
            msg("m1b", "th", "r1", "2026-01-01T10:05", "also cover offline mode"),       # steer, same run
            msg("d1", "th", "r1", "2026-01-01T10:06", "Result from a delegated task", by="agent", source="server"),
            msg("n1", "th", "r1", "2026-01-01T10:07", "Notice", by="user", source="provider"),
            msg("a1", "th", "r1", "2026-01-01T10:09", "Here is the plan", role="assistant"),
            msg("m2", "th", "r2", "2026-01-01T10:15", "The plan misses conflicts"),       # reaction to r1
            msg("m3", "th", "r3", "2026-01-01T10:35", "Now write release notes", source="mobile"),
            msg("m4", "th", None, "2026-01-01T10:55", "/compact"),
        ])
        db.commit()
        db.close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_human_message_filter(self):
        messages, _ = extract_t3.extract(str(self.db))
        self.assertEqual(["m1", "m1b", "m2", "m3", "m4"], [m["id"] for m in messages])

    def test_distinct_runs_and_reaction_vs_steer(self):
        _, runs = extract_t3.extract(str(self.db))
        by = {r["run_id"]: r for r in runs}
        self.assertEqual(["r1", "r2", "r3"], sorted(by))  # r1 carried two human messages; codex run skipped
        self.assertEqual("Plan the sync feature", by["r1"]["request"])
        self.assertEqual(["m1b"], by["r1"]["steer_ids"])
        self.assertEqual("m2", by["r1"]["reaction_id"])
        self.assertEqual("m3", by["r2"]["reaction_id"])
        self.assertEqual(("fable-5-2", "high"), (by["r2"]["model"][7:], by["r2"]["effort"]))

    def test_snapshot_is_not_modified(self):
        before = self.db.read_bytes()
        extract_t3.extract(str(self.db))
        self.assertEqual(before, self.db.read_bytes())


class ReactionRules(unittest.TestCase):
    def runs(self):
        base = dict(model="m", effort=None, reply_end="", max_context_tokens=None)
        return [dict(base, run_id="a", thread="t", requested_at="01", completed_at="05", request="task a", request_ids=["q1"]),
                dict(base, run_id="b", thread="t", requested_at="03", completed_at="06", request="task b", request_ids=["q2"])]

    def test_reaction_after_completed_at_else_pre_result(self):
        messages = [{"id": "q1", "thread": "t", "at": "01", "text": "task a"},
                    {"id": "q2", "thread": "t", "at": "03", "text": "task b"},
                    {"id": "q3", "thread": "t", "at": "07", "text": "looks good"}]
        out = {r["run_id"]: r for r in mfrlib.assign_reactions(self.runs(), messages)}
        # q2 was sent while run a was going: steer, not a reaction.
        self.assertEqual(["q2"], out["a"]["steer_ids"])
        # q3 came after run b completed too, so it reacts to b, not a.
        self.assertEqual(("pre_result", None), (out["a"]["follow_state"], out["a"]["reaction_id"]))
        self.assertEqual(("reaction", "q3"), (out["b"]["follow_state"], out["b"]["reaction_id"]))

    def test_no_later_message_is_end(self):
        out = mfrlib.assign_reactions(self.runs()[:1], [{"id": "q1", "thread": "t", "at": "01", "text": "x"}])
        self.assertEqual("end", out[0]["follow_state"])


class ControlCommands(unittest.TestCase):
    def test_session_commands_are_not_tasks(self):
        for text in ("/compact", "/compact keep the plan", "/clear", "/reload-plugins", "/reload-skills",
                     "/mcp", "/output-style", "/칟ㅁㄱ"):
            self.assertTrue(mfrlib.is_control(text), text)
        for text in ("/fstack fix the login bug", "/init", "add /compact support to the CLI", ""):
            self.assertFalse(mfrlib.is_control(text), text)

    def test_control_runs_excluded_and_control_reaction_is_session(self):
        base = dict(model="m", effort="low", reply_end="", max_context_tokens=None, steer_ids=[])
        runs = [dict(base, run_id="1", thread="t", requested_at="01", request="build it", follow_state="reaction", reaction_id="c"),
                dict(base, run_id="2", thread="t", requested_at="02", request="/compact", follow_state="reaction", reaction_id="x"),
                dict(base, run_id="3", thread="t", requested_at="03", request="/fstack review", follow_state="end", reaction_id=None)]
        eps = mfrlib.group_episodes(runs, {"x": "accept"}, {"c": "/compact", "x": "/fstack review"})
        self.assertEqual(1, len(eps))
        self.assertEqual(["1", "3"], eps[0]["run_ids"])


class EpisodeBoundary(unittest.TestCase):
    def test_new_topic_starts_an_episode(self):
        base = dict(model="claude-opus-5-5", effort="medium", reply_end="", max_context_tokens=None, steer_ids=[])
        runs = [dict(base, run_id="1", thread="t", requested_at="01", request="a", follow_state="reaction", reaction_id="r1"),
                dict(base, run_id="2", thread="t", requested_at="02", request="b", follow_state="reaction", reaction_id="r2"),
                dict(base, run_id="3", thread="t", requested_at="03", request="c", follow_state="reaction", reaction_id="r3"),
                dict(base, run_id="4", thread="u", requested_at="01", request="d", follow_state="end", reaction_id=None)]
        labels = {"r1": "fix", "r2": "new_topic", "r3": "fix"}
        eps = mfrlib.group_episodes(runs, labels, {})
        self.assertEqual([["1", "2"], ["3"], ["4"]], [e["run_ids"] for e in eps])
        self.assertEqual([1, 1, 0], [e["fix"] for e in eps])
        self.assertEqual("one_fix", eps[0]["outcome"])
        # Rerun gives identical output.
        self.assertEqual(eps, mfrlib.group_episodes(runs, labels, {}))


class LogExtraction(unittest.TestCase):
    def test_log_only_path(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            proj = tmp / "projects" / "-synthetic-project"
            (proj / "subagents").mkdir(parents=True)
            shutil.copy(HERE / "fixtures" / "session-a.jsonl", proj / "session-a.jsonl")
            shutil.copy(HERE / "fixtures" / "session-a.jsonl", proj / "subagents" / "agent-1.jsonl")
            messages, runs = extract_logs.extract(tmp / "projects")
            self.assertEqual(["Add a dark mode toggle to the settings screen",
                              "The toggle does not save after restart", "/compact",
                              "/release-notes draft notes for version 2"], [m["text"] for m in messages])
            self.assertEqual(3, len(runs))  # the /compact turn has only a synthetic reply
            first = runs[0]
            self.assertEqual(("claude-sonnet-5-5", "high", 3025), (first["model"], first["effort"], first["max_context_tokens"]))
            self.assertEqual("Added the toggle.", first["reply_end"])
            self.assertEqual(messages[1]["id"], first["reaction_id"])
            self.assertIsNone(runs[1]["effort"])  # effort unknown when the log has none
            items, key = export_items.build(messages, runs)
            self.assertEqual(1, len(items))  # reaction "/compact" is a session command, not an item
            self.assertNotIn("sonnet", json.dumps(items))
            labels = episodes.message_labels(key, [{items[0]["id"]: "fix"}])
            eps = mfrlib.group_episodes(runs, labels, {m["id"]: m["text"] for m in messages})
            self.assertEqual(1, eps[0]["fix"])
        finally:
            shutil.rmtree(tmp)


class Practice(unittest.TestCase):
    def test_over_and_under_picks(self):
        cards = [{"id": "1-1", "round": 1, "reference": ["Sonnet"], "evidence": "inferred"},
                 {"id": "1-2", "round": 1, "reference": ["Sonnet", "Opus"], "evidence": "observed"},
                 {"id": "1-3", "round": 1, "reference": ["Fable"], "evidence": "replay"},
                 {"id": "2-1", "round": 2, "reference": ["Haiku"], "evidence": "inferred"}]
        s = score_practice.score(cards, {"1-1": "Opus", "1-2": "opus", "1-3": "Sonnet", "2-1": "Haiku"}, 1)
        self.assertEqual((3, 1, 1, 1), (s["n"], s["right"], s["over"], s["under"]))
        self.assertEqual({"n": 1, "right": 0}, s["by_evidence"]["replay"])


if __name__ == "__main__":
    unittest.main()
