"""Tests for the model-fit-review scripts on small synthetic fixtures.
Run: python3 -I -S -B -m unittest discover -s <skill>/tests -v
"""
from __future__ import annotations

import io
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import episodes  # noqa: E402
import export_items  # noqa: E402
import extract_logs  # noqa: E402
import extract_t3  # noqa: E402
import mfrlib  # noqa: E402
import score_practice  # noqa: E402
import snapshot_db  # noqa: E402

SCHEMA = """
create table orchestration_v2_projection_runs (run_id text primary key, thread_id text, ordinal integer,
  provider text, status text, requested_at text, completed_at text, payload_json text);
create table orchestration_v2_projection_messages (message_id text primary key, thread_id text, run_id text,
  role text, created_at text, payload_json text);
create table orchestration_v2_projection_provider_threads (provider_thread_id text primary key, thread_id text,
  provider text, payload_json text);
"""


def msg(mid, thread, run, at, text, role="user", by="user", source="web"):
    payload = {"text": text}
    if role == "user":
        payload.update(createdBy=by, creationSource=source)
    return (mid, thread, run, role, at, json.dumps(payload))


def run(rid, thread, req, done, model="claude-opus-5-5", effort="medium", status="completed", provider="claudeAgent"):
    payload = {"modelSelection": {"model": model, "options": [{"id": "effort", "value": effort}]}}
    return (rid, thread, 1, provider, status, req, done, json.dumps(payload))


def make_db(path: Path, runs=(), messages=(), natives=()):
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.executemany("insert into orchestration_v2_projection_runs values (?,?,?,?,?,?,?,?)", runs)
    db.executemany("insert into orchestration_v2_projection_messages values (?,?,?,?,?,?)", messages)
    db.executemany("insert into orchestration_v2_projection_provider_threads values (?,?,?,?)",
                   [(f"pt{i}", t, "claudeAgent", json.dumps({"nativeThreadRef": {"driver": "claudeAgent", "nativeId": n}}))
                    for i, (n, t) in enumerate(natives)])
    db.commit()
    db.close()


class T3Fixture(unittest.TestCase):
    """Thread th: an agent-initiated run (ra, a delegation result) completes
    between r1 and the user's next message. Thread mx mixes Claude and Codex."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db = self.tmp / "snap.sqlite"
        make_db(self.db, runs=[
            run("r1", "th", "2026-01-01T10:00", "2026-01-01T10:10"),
            run("ra", "th", "2026-01-01T10:11", "2026-01-01T10:12"),
            run("r2", "th", "2026-01-01T10:15", "2026-01-01T10:30", model="claude-fable-5-2", effort="high"),
            run("r3", "th", "2026-01-01T10:35", "2026-01-01T10:50"),
            run("rx", "th", "2026-01-01T10:58", "2026-01-01T11:00", provider="codex"),
            run("c1", "mx", "2026-01-02T12:00", "2026-01-02T12:05"),
            run("x1", "mx", "2026-01-02T12:06", "2026-01-02T12:10", provider="codex"),
            run("c2", "mx", "2026-01-02T12:12", "2026-01-02T12:20"),
            run("x2", "mx", "2026-01-02T12:21", "2026-01-02T12:25", provider="codex"),
            run("c3", "mx", "2026-01-02T12:30", "2026-01-02T12:40"),
        ], messages=[
            msg("m1", "th", "r1", "2026-01-01T10:00", "Plan the sync feature"),
            msg("m1b", "th", "r1", "2026-01-01T10:05", "also cover offline mode"),       # steer, same run
            msg("d1", "th", "r1", "2026-01-01T10:06", "Result from a delegated task", by="agent", source="server"),
            msg("n1", "th", "r1", "2026-01-01T10:07", "Notice", by="user", source="provider"),
            msg("s1", "th", "r1", "2026-01-01T10:08", "Which store? -> SQLite", source="server"),  # question answer
            msg("a1", "th", "r1", "2026-01-01T10:09", "Here is the plan", role="assistant"),
            msg("d2", "th", "ra", "2026-01-01T10:11", "Delegated result: sync module done", by="agent", source="server"),
            msg("a2", "th", "ra", "2026-01-01T10:12", "The delegated sync module is merged", role="assistant"),
            msg("m2", "th", "r2", "2026-01-01T10:15", "The plan misses conflicts"),
            msg("m3", "th", "r3", "2026-01-01T10:35", "Now write release notes", source="mobile"),
            msg("m4", "th", None, "2026-01-01T10:55", "/compact"),
            msg("k1", "mx", "c1", "2026-01-02T12:00", "Draft the API"),
            msg("k2", "mx", "x1", "2026-01-02T12:06", "Codex: lint it"),
            msg("k3", "mx", "c2", "2026-01-02T12:12", "Add pagination"),
            msg("g1", "mx", "x2", "2026-01-02T12:21", "Delegated codex task", by="agent", source="mcp"),
            msg("k5", "mx", "c3", "2026-01-02T12:30", "Looks right"),
        ])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def extract(self):
        messages, runs, timeline, answers = extract_t3.extract(str(self.db))
        return messages, {r["run_id"]: r for r in runs}, timeline, answers

    def test_human_message_filter_and_answers(self):
        messages, _, _, answers = self.extract()
        self.assertEqual(["k1", "k2", "k3", "k5", "m1", "m1b", "m2", "m3", "m4"], [m["id"] for m in messages])  # by thread, time
        self.assertEqual(1, len(answers))  # s1: creationSource='server' answer, never a reaction or steer

    def test_agent_run_between_run_and_reaction_supersedes(self):
        _, by, _, _ = self.extract()
        self.assertEqual(["c1", "c2", "c3", "r1", "r2", "r3", "ra"], sorted(by))  # Codex runs are timeline only
        self.assertEqual(["m1b"], by["r1"]["steer_ids"])
        self.assertEqual(("superseded", None, "ra"),
                         (by["r1"]["follow_state"], by["r1"]["reaction_id"], by["r1"]["superseded_by"]))
        self.assertEqual("m2", by["r1"]["next_id"])
        self.assertEqual(("agent", "reaction", "m2"),
                         (by["ra"]["initiator"], by["ra"]["follow_state"], by["ra"]["reaction_id"]))
        self.assertEqual("m3", by["r2"]["reaction_id"])
        self.assertEqual("m4", by["r3"]["reaction_id"])  # rx completed after m4
        self.assertEqual(("fable-5-2", "high"), (by["r2"]["model"][7:], by["r2"]["effort"]))

    def test_mixed_provider_thread(self):
        _, by, timeline, _ = self.extract()
        self.assertIn("x2", {t["run_id"] for t in timeline})
        # c1's next human message started a Codex run: never a reaction to a Claude run.
        self.assertEqual(("other_provider", None), (by["c1"]["follow_state"], by["c1"]["reaction_id"]))
        # An agent-initiated Codex run completed before the user's next message.
        self.assertEqual(("superseded", "x2"), (by["c2"]["follow_state"], by["c2"]["superseded_by"]))
        self.assertEqual("end", by["c3"]["follow_state"])
        messages, runs, _, _ = extract_t3.extract(str(self.db))
        lines = mfrlib.summary(messages, runs)
        self.assertIn("human messages 9  attached to Claude runs or unattached 8", lines[1])

    def test_window(self):
        messages, runs, _, _ = extract_t3.extract(str(self.db))
        mw, rw = mfrlib.apply_window(messages, runs, since="2026-01-02", until="2026-01-02")
        self.assertEqual(["c1", "c2", "c3"], sorted(r["run_id"] for r in rw))
        self.assertEqual({"k1", "k2", "k3", "k5"}, {m["id"] for m in mw})
        mw, rw = mfrlib.apply_window(messages, runs, until="2026-01-01")
        self.assertEqual(["r1", "r2", "r3", "ra"], sorted(r["run_id"] for r in rw))

    def test_cli_window_and_counts(self):
        out = io.StringIO()
        argv = sys.argv
        sys.argv = ["extract_t3.py", "--db", str(self.db), "--out", str(self.tmp / "o"), "--since", "2026-01-02"]
        try:
            with redirect_stdout(out):
                self.assertEqual(0, extract_t3.main())
        finally:
            sys.argv = argv
        text = out.getvalue()
        self.assertIn("window 2026-01-02..… UTC", text)
        self.assertIn("Claude runs 3  human-initiated 3", text)
        self.assertIn("question answers (not counted) 0", text)
        self.assertEqual(3, len(mfrlib.read_jsonl(self.tmp / "o" / "runs.jsonl")))

    def test_snapshot_is_not_modified(self):
        before = self.db.read_bytes()
        extract_t3.extract(str(self.db))
        self.assertEqual(before, self.db.read_bytes())


class ReactionRules(unittest.TestCase):
    def runs(self):
        base = dict(model="m", effort=None, reply_end="", max_context_tokens=None, initiator="human", provider="claude")
        return [dict(base, run_id="a", thread="t", requested_at="01", completed_at="05", request="task a", request_ids=["q1"]),
                dict(base, run_id="b", thread="t", requested_at="03", completed_at="06", request="task b", request_ids=["q2"])]

    def test_reaction_after_completed_at_else_superseded(self):
        messages = [{"id": "q1", "thread": "t", "at": "01", "text": "task a"},
                    {"id": "q2", "thread": "t", "at": "03", "text": "task b"},
                    {"id": "q3", "thread": "t", "at": "07", "text": "looks good"}]
        out = {r["run_id"]: r for r in mfrlib.assign_reactions(self.runs(), messages)}
        # q2 was sent while run a was going: steer, not a reaction.
        self.assertEqual(["q2"], out["a"]["steer_ids"])
        # q3 came after run b completed too, so it reacts to b, not a.
        self.assertEqual(("superseded", None, "b"),
                         (out["a"]["follow_state"], out["a"]["reaction_id"], out["a"]["superseded_by"]))
        self.assertEqual(("reaction", "q3"), (out["b"]["follow_state"], out["b"]["reaction_id"]))

    def test_timeline_run_not_in_runs_supersedes(self):
        messages = [{"id": "q1", "thread": "t", "at": "01", "text": "task a"},
                    {"id": "q3", "thread": "t", "at": "09", "text": "ok"}]
        timeline = [{"run_id": "a", "thread": "t", "provider": "claude", "completed_at": "05"},
                    {"run_id": "z", "thread": "t", "provider": "codex", "completed_at": "08"}]
        out = mfrlib.assign_reactions(self.runs()[:1], messages, timeline)
        self.assertEqual(("superseded", "z"), (out[0]["follow_state"], out[0]["superseded_by"]))

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
        texts = {"c": "/compact", "x": "/fstack review"}
        eps = mfrlib.group_episodes(runs, {"x": "accept"}, texts)
        self.assertEqual(1, len(eps))
        self.assertEqual(["1", "3"], eps[0]["run_ids"])
        # The control run's reaction is never exported, so it is not "unlabeled".
        self.assertEqual(0, episodes.unlabeled_reactions(runs, texts, {}))


class EpisodeBoundary(unittest.TestCase):
    def runs(self):
        base = dict(model="claude-opus-5-5", effort="medium", reply_end="", max_context_tokens=None, steer_ids=[])
        return [dict(base, run_id="1", thread="t", requested_at="01", request="a", follow_state="reaction", reaction_id="r1"),
                dict(base, run_id="2", thread="t", requested_at="02", request="b", follow_state="reaction", reaction_id="r2"),
                dict(base, run_id="3", thread="t", requested_at="03", request="c", follow_state="reaction", reaction_id="r3"),
                dict(base, run_id="4", thread="u", requested_at="01", request="d", follow_state="end", reaction_id=None)]

    def test_new_topic_starts_an_episode(self):
        labels = {"r1": "fix", "r2": "new_topic", "r3": "fix"}
        eps = mfrlib.group_episodes(self.runs(), labels, {})
        self.assertEqual([["1", "2"], ["3"], ["4"]], [e["run_ids"] for e in eps])
        self.assertEqual([1, 1, 0], [e["fix"] for e in eps])
        self.assertEqual("one_fix", eps[0]["outcome"])
        # Rerun gives identical output.
        self.assertEqual(eps, mfrlib.group_episodes(self.runs(), labels, {}))

    def test_exclude_thread(self):
        eps = mfrlib.group_episodes(self.runs(), {}, {}, exclude_threads=["t"])
        self.assertEqual([["4"]], [e["run_ids"] for e in eps])


class LabelPrecedence(unittest.TestCase):
    def test_hand_labels_win_in_any_order(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            key = {"i1": {"message_id": "x", "run_id": "1", "kind": "reaction"},
                   "i2": {"message_id": "y", "run_id": "1", "kind": "steer"}}
            hand, clf = tmp / "labels_hand.json", tmp / "labels_haiku_1.json"
            hand.write_text(json.dumps({"i1": "fix"}))
            clf.write_text(json.dumps({"i1": "accept", "i2": "add"}))
            for order in ([str(hand), str(clf)], [str(clf), str(hand)]):
                c, h = episodes.load_labels([], order)
                labels = episodes.message_labels(key, c, h)
                self.assertEqual({"reaction": {"x": "fix"}, "steer": {"y": "add"}}, labels, order)
            c, h = episodes.load_labels([str(hand)], [str(clf)])
            self.assertEqual("fix", episodes.message_labels(key, c, h)["reaction"]["x"])
        finally:
            shutil.rmtree(tmp)


class Items(unittest.TestCase):
    def runs_and_messages(self):
        base = dict(model="claude-opus-5-5", effort="medium", max_context_tokens=None, initiator="human")
        runs, messages = [], []
        for i in range(30):
            messages.append({"id": f"q{i}", "thread": "t", "at": f"{i:03d}", "text": f"request {i}"})
            messages.append({"id": f"s{i}", "thread": "t", "at": f"{i:03d}a", "text": f"steer {i}"})
            runs.append(dict(base, run_id=str(i), thread="t", requested_at=f"{i:03d}", request=f"task {i} for Opus 5.5",
                             reply_end="claude-opus-5-5 says done; 소넷이면 충분", follow_state="reaction",
                             reaction_id=f"q{i + 1}", steer_ids=[f"s{i}"]))
        return messages, runs

    def test_kind_mask_and_random_reaction_calibration(self):
        messages, runs = self.runs_and_messages()
        items, key = export_items.build(messages, runs)
        self.assertEqual({"reaction", "steer"}, {it["kind"] for it in items})
        self.assertTrue(all(it["assistant_reply_end"] == "" for it in items if it["kind"] == "steer"))
        dump = json.dumps(items, ensure_ascii=False).lower()
        for name in ("opus", "claude-", "소넷"):
            self.assertNotIn(name, dump)
        calib = export_items.calibration(items, 10, 7)
        self.assertEqual(10, len(calib))
        self.assertTrue(all(it["kind"] == "reaction" for it in calib))
        self.assertEqual(calib, export_items.calibration(items, 10, 7))
        self.assertNotEqual([it["id"] for it in calib], [it["id"] for it in items if it["kind"] == "reaction"][:10])

    def test_mask_models(self):
        self.assertEqual("[model] or [model], [model]을 써요, [model] high",
                         mfrlib.mask_models("Opus 5.5 or claude-sonnet-5-5, 소넷을 써요, Haiku high"))
        self.assertEqual("a sonnetized word", mfrlib.mask_models("a sonnetized word"))

    def test_episode_items(self):
        runs = [{"run_id": str(i), "request": "x" * 300, "initiator": "human"} for i in range(8)]
        runs.append({"run_id": "a", "request": "Delegated task node: result", "initiator": "agent"})
        items, key = export_items.build_episodes([{"episode": "e0000", "run_ids": [r["run_id"] for r in runs]}], runs)
        self.assertEqual(8, items[0]["n_requests"])
        self.assertEqual(6, len(items[0]["requests"]))
        self.assertEqual(221, len(items[0]["requests"][0]))  # 220 characters and an ellipsis
        self.assertEqual({"episode": "e0000"}, key[items[0]["id"]])
        self.assertEqual("user", items[0]["source"])
        items, _ = export_items.build_episodes([{"episode": "e0001", "run_ids": ["a"]}], runs)
        self.assertEqual(("delegated", 1), (items[0]["source"], items[0]["n_requests"]))


class LogExtraction(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.proj = self.tmp / "projects" / "-synthetic-project"
        (self.proj / "subagents").mkdir(parents=True)
        for name in ("session-a", "session-b"):
            shutil.copy(HERE / "fixtures" / f"{name}.jsonl", self.proj / f"{name}.jsonl")
        shutil.copy(HERE / "fixtures" / "session-a.jsonl", self.proj / "subagents" / "agent-1.jsonl")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_log_only_path(self):
        messages, runs, _ = extract_logs.extract(self.tmp / "projects")
        messages = [m for m in messages if m["thread"] == "session-a"]
        runs = [r for r in runs if r["thread"] == "session-a"]
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
        eps = mfrlib.group_episodes(runs, labels["reaction"], {m["id"]: m["text"] for m in messages})
        self.assertEqual(1, eps[0]["fix"])

    def test_injected_prompts_start_agent_runs(self):
        messages, runs, _ = extract_logs.extract(self.tmp / "projects")
        texts = [m["text"] for m in messages if m["thread"] == "session-b"]
        self.assertEqual(["Plan the export feature", "Looks good, ship it", "Goal: ship build 4 from the develop branch to testers.",
                          "Check the export code /review", "Fix both findings [Image #1]"], texts)
        b = [r for r in runs if r["thread"] == "session-b"]
        self.assertEqual(["human", "agent", "human", "agent", "agent", "human", "human", "human"], [r["initiator"] for r in b])
        # The delegation result run completed before "Looks good": it gets the reaction.
        self.assertEqual(("superseded", b[1]["run_id"]), (b[0]["follow_state"], b[0]["superseded_by"]))
        self.assertEqual(("reaction", messages[[m["text"] for m in messages].index("Looks good, ship it")]["id"]),
                         (b[1]["follow_state"], b[1]["reaction_id"]))
        self.assertEqual(("superseded", b[4]["run_id"]), (b[2]["follow_state"], b[2]["superseded_by"]))
        self.assertEqual("Check the export code /review", b[6]["request"])

    def test_t3_db_is_the_authority(self):
        db = self.tmp / "t3.sqlite"
        make_db(db, messages=[
            msg("h1", "tb", None, "2026-01-06T09:00:00.500Z", "Plan the export feature"),
            msg("h2", "tb", None, "2026-01-06T09:05:01Z", "Looks good, ship it"),
            msg("h3", "tb", None, "2026-01-06T09:13:00.800Z", "Check the export code $review"),
            msg("h4", "tb", None, "2026-01-06T09:16:00.200Z", "[shot.png](t3-context://v1/file/x) Fix both findings"),
        ], natives=[("session-b", "tb")])
        messages, runs, stats = extract_logs.extract(self.tmp / "projects", str(db))
        b_texts = [m["text"] for m in messages if m["thread"] == "session-b"]
        self.assertNotIn("Goal: ship build 4 from the develop branch to testers.", b_texts)  # no T3 match
        self.assertEqual(4, len(b_texts))
        self.assertEqual(1, stats["mapped human, no T3 match -> agent"])
        self.assertEqual(4, stats["unmapped human"])  # session-a is not in the DB: log rules apply

    def test_prompt_matching_normalizes(self):
        self.assertTrue(mfrlib.prompts_match("/review check it", "$review check it", 2))
        self.assertTrue(mfrlib.prompts_match("/review", "please look $review", 5))
        self.assertFalse(mfrlib.prompts_match("/review", "please look $review", 120))
        self.assertTrue(mfrlib.prompts_match("[File: a.zip; ref=1] apply this", "[a.zip](t3-context://v1/file/1) apply this", 1))
        self.assertFalse(mfrlib.prompts_match("ship it", "ship it", 3600))


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "odd #dir? 'x'" / "state v2.sqlite"
        self.src.parent.mkdir()
        db = sqlite3.connect(self.src)
        db.execute("pragma journal_mode=WAL")
        db.execute("create table t (x)")
        db.execute("insert into t values (42)")
        db.commit()
        db.close()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_copy_is_delete_mode_without_sidecars(self):
        dest = self.tmp / "out 'q'" / "snap.sqlite"
        snapshot_db.copy(self.src, dest)
        self.assertFalse(Path(str(dest) + "-wal").exists() or Path(str(dest) + "-shm").exists())
        db = sqlite3.connect(mfrlib.ro_uri(dest), uri=True)
        self.assertEqual("delete", db.execute("pragma journal_mode").fetchone()[0])
        self.assertEqual(42, db.execute("select x from t").fetchone()[0])
        db.close()
        self.assertFalse(Path(str(dest) + "-wal").exists() or Path(str(dest) + "-shm").exists())
        with self.assertRaises(SystemExit):
            snapshot_db.copy(self.src, dest)
        snapshot_db.copy(self.src, dest, force=True)
        Path(str(dest) + "-wal").write_text("stale")
        gone = snapshot_db.remove(dest)
        self.assertEqual(2, len(gone))
        self.assertFalse(dest.exists() or Path(str(dest) + "-wal").exists())

    def test_missing_source_is_a_clean_error(self):
        argv = sys.argv
        sys.argv = ["snapshot_db.py", "--source", str(self.tmp / "nope.sqlite"), "--dest", str(self.tmp / "d"), "--yes"]
        err = io.StringIO()
        try:
            with redirect_stderr(err):
                self.assertEqual(2, snapshot_db.main())
        finally:
            sys.argv = argv
        self.assertIn("source not found", err.getvalue())


@unittest.skipUnless(shutil.which("git"), "git not installed")
class OutputDirCheck(unittest.TestCase):
    def test_refuses_dir_inside_repo_unless_ignored(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            subprocess.run(["git", "init", "-q", str(tmp / "repo")], check=True)
            inside = tmp / "repo" / "_review" / "data"
            self.assertIsNotNone(mfrlib.check_output_dir(inside))
            self.assertIsNone(mfrlib.check_output_dir(inside, allow_repo=True))
            (tmp / "repo" / ".gitignore").write_text("_review/\n")
            self.assertIsNone(mfrlib.check_output_dir(inside))
            self.assertIsNone(mfrlib.check_output_dir(tmp / "outside"))
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
