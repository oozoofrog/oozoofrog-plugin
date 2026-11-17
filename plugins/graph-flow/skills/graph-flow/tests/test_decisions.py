import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from graphflow import core, decisions, plan, state, store

from human_support import legacy_run, recorded_question

ACTOR = {"role": "leader", "node": None, "session": "test"}
HUMAN = {"role": "human", "node": None, "session": None}


class DecisionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.home = self.root / "home"
        self.env = mock.patch.dict(os.environ, {"GF_HOME": str(self.home)})
        self.env.start()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.run = legacy_run(self.repo, "r1", ACTOR)
        self.set_plan()
        decisions.ensure_key({'role': 'human'})

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def set_plan(self, goal="a"):
        raw = {"schema_version": 1, "goal": "test", "nodes": [
            {"id": n, "goal": goal, "kind": "work", "lane": 1, "grade": "daily",
             "owns": [n + ".py"], "checks": [{"id": "unit", "type": "cmd", "run": "true"}]}
            for n in ("a", "b")]}
        normalized, _ = plan.normalize(raw)
        with store.transaction(self.run) as tx:
            revision, sha = tx.write_plan(normalized)
            tx.append("plan.set", {"revision": revision, "plan_sha256": sha,
                      "fingerprints": {n["id"]: state.fingerprint(n) for n in normalized["nodes"]},
                      "constraints_applied": []}, ACTOR)

    def derive(self):
        with store.transaction(self.run) as tx:
            return state.derive(tx.plan, tx.events)

    def ask(self, **kw):
        args = dict(kind="information", question="Approve?", node=None, check=None,
                    purpose=None, evidence=None, actor=ACTOR)
        args.update(kw)
        return decisions.ask(self.run, **args)

    def answer(self, did, **kw):
        args = dict(outcome="answered", answer_text="Yes ✓", source="terminal", actor=HUMAN)
        args.update(kw)
        return decisions.answer(self.run, did, **args)

    def error(self, code, exit_code, fn, *args, **kw):
        before = store.events(self.run)
        with self.assertRaises(core.GFError) as caught:
            fn(*args, **kw)
        self.assertEqual((caught.exception.code, caught.exception.exit_code), (code, exit_code))
        self.assertEqual(store.events(self.run), before)

    def event(self, type_, **data):
        with store.transaction(self.run) as tx:
            return tx.append(type_, data, ACTOR)

    def test_ask_defaults_and_recovered_sequence(self):
        with open(str(self.run / "events.jsonl"), "ab") as f:
            f.write(b'{')
        data = self.ask()
        ev = store.events(self.run)[-1]
        self.assertEqual(data, ev["data"])
        self.assertEqual(data["id"], "d%d" % ev["seq"])
        self.assertEqual(data["evidence"], {"command": None, "files": [], "checks": []})
        self.assertEqual(data["purpose"], "free")
        self.assertIsNone(data["submission"])
        self.assertEqual(store.events(self.run)[-2]["type"], "log.recovered")

    def test_ask_validation(self):
        for bad in (None, "", "other", [], {}):
            self.error("bad_kind", 2, self.ask, kind=bad)
        for bad in ("", "other", [], {}):
            self.error("bad_purpose", 2, self.ask, purpose=bad)
        for bad in (None, "", "  ", 42):
            self.error("bad_question", 2, self.ask, question=bad)
        self.error("unknown_node", 4, self.ask, node="missing")
        self.error("bad_purpose", 2, self.ask, purpose="hold")
        for purpose in ("free",):
            self.assertEqual(self.ask(purpose=purpose)["purpose"], purpose)

    def test_submission_binding_and_stale_restart(self):
        self.assertIsNone(self.ask(node="a")["submission"])
        self.event("node.start", node="a", attempt=1, base={})
        sub = self.event("node.submit", node="a", attempt=1)
        evidence = {"command": "publish", "files": ["a.py"], "checks": ["unit"]}
        data = self.ask(node="a", check="unit", evidence=evidence)
        self.assertEqual(data["submission"], sub["seq"])
        self.assertEqual(data["evidence"], evidence)
        self.assertEqual(data["check"], "unit")
        self.event("node.start", node="a", attempt=2, base={})
        self.assertTrue(self.derive()["decisions"][data["id"]]["stale"])
        self.error("stale_decision", 4, self.answer, data["id"])

    def test_basis_invalidates_decision(self):
        data = self.ask(node="a")
        self.set_plan(goal="changed")
        self.error("stale_decision", 4, self.answer, data["id"])

    def test_answer_signature_and_key_replacement(self):
        data = self.ask()
        answer = self.answer(data["id"])
        self.assertEqual(store.events(self.run)[-1]["data"], answer)
        data = self.derive()["decisions"][data["id"]]
        self.assertEqual(answer["sig"], core.human_sig("r1", data["id"], "answered", "Yes ✓", data))
        self.assertTrue(decisions.verify("r1", data["id"], answer, data))
        self.assertTrue(self.derive()["decisions"][data["id"]]["verified"])
        self.error("already_answered", 4, self.answer, data["id"])
        (self.home / "human.key").write_bytes(b'x' * 32)
        self.assertFalse(self.derive()["decisions"][data["id"]]["verified"])
        self.assertFalse(decisions.verify("r1", data["id"], answer, data))

    def test_nonhuman_actors_cannot_answer_or_create_key(self):
        data = self.ask()
        original_key = (self.home / "human.key").read_bytes()
        for role in ("leader", "worker", "reviewer"):
            actor = {"role": role, "node": None if role == "leader" else "a", "session": "agent"}
            for source in ("terminal", "dashboard"):
                with self.subTest(role=role, source=source):
                    self.error("forbidden", core.EXIT_FORBIDDEN, self.answer,
                               data["id"], source=source, actor=actor)
                    self.assertEqual((self.home / "human.key").read_bytes(), original_key)

    def test_nonhuman_actor_is_refused_before_validation_or_io(self):
        original_key = (self.home / "human.key").read_bytes()
        for role in ("leader", "worker", "reviewer"):
            with self.subTest(role=role):
                with mock.patch.object(decisions, "ensure_key") as key, \
                        mock.patch.object(store, "transaction") as transaction:
                    self.error("forbidden", core.EXIT_FORBIDDEN, decisions.answer,
                               self.root / "missing-run", "missing", "invalid", "", "invalid",
                               {"role": role, "node": None, "session": None})
                key.assert_not_called()
                transaction.assert_not_called()
                self.assertEqual((self.home / "human.key").read_bytes(), original_key)

    def test_all_outcomes_and_sources(self):
        for kind in ("review", "authorization", "direction", "information"):
            valid = ("approved", "rejected", "revision_requested") if kind in ("review", "authorization") else ("answered",)
            for outcome in ("approved", "rejected", "revision_requested", "answered", "bad", None):
                data = (recorded_question(self.run,kind,"Approve?",None,None,"free",None,ACTOR)
                        if kind in ("review", "authorization") else self.ask(kind=kind))
                if outcome in valid:
                    result = self.answer(data["id"], outcome=outcome, source="dashboard")
                    self.assertEqual(result["outcome"], outcome)
                    self.assertEqual(result["source"], "dashboard")
                else:
                    self.error("bad_outcome", 2, self.answer, data["id"], outcome=outcome)
        data = self.ask()
        for source in (None, "agent", "", [], {}):
            self.error("bad_source", 2, self.answer, data["id"], source=source)
        self.error("unknown_decision", 4, self.answer, "d9999")

    def test_verify_junk_and_tampering(self):
        data = self.ask()
        answer = self.answer(data["id"])
        for junk in (None, [], 42, "x", {}, {"outcome": []},
                     dict(answer, sig=None), dict(answer, sig="é"),
                     dict(answer, sig="\ud800"), dict(answer, answer=[]),
                     dict(answer, answer="changed"), dict(answer, outcome="rejected")):
            self.assertIs(decisions.verify("r1", data["id"], junk), False)
        self.assertFalse(decisions.verify("other", data["id"], answer))
        self.assertFalse(decisions.verify("r1", "other", answer))
        (self.home / "human.key").unlink()
        self.assertFalse(decisions.verify("r1", data["id"], answer, data))

    def test_ensure_key_mode_stability_and_atomic_install(self):
        (self.home / "human.key").unlink()
        with mock.patch.object(store.os, "replace", wraps=store.os.replace) as replace:
            path = decisions.ensure_key({'role': 'human'})
            self.assertEqual(replace.call_count, 1)
        original = path.read_bytes()
        self.assertEqual(len(original), 32)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        with mock.patch.object(store, "atomic_write") as write:
            self.assertEqual(decisions.ensure_key({'role': 'human'}), path)
            write.assert_not_called()
        self.assertEqual(path.read_bytes(), original)
        path.write_bytes(b'preserve existing even if empty')
        decisions.ensure_key({'role': 'human'})
        self.assertEqual(path.read_bytes(), b'preserve existing even if empty')

    def test_ensure_key_concurrent_processes(self):
        home = self.root / "fresh-home"
        code = ("import sys; sys.path.insert(0, sys.argv[1]); "
                "from graphflow import decisions; "
                "print(decisions.ensure_key({'role': 'human'}).read_bytes().hex())")
        env = dict(os.environ, GF_HOME=str(home))
        procs = [subprocess.Popen([sys.executable, "-I", "-S", "-B", "-c", code, str(SCRIPTS)],
                 env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        outputs = []
        for proc in procs:
            out, err = proc.communicate(timeout=20)
            self.assertEqual(proc.returncode, 0, err.decode())
            outputs.append(out.decode().strip())
        self.assertEqual(outputs, [(home / "human.key").read_bytes().hex()] * 2)
        self.assertEqual(len(bytes.fromhex(outputs[0])), 32)

    def test_wait_timeout_unknown_and_answer_thread(self):
        self.error("unknown_decision", 4, decisions.wait, self.run, "missing", 0)
        data = self.ask()
        self.error("wait_timeout", 1, decisions.wait, self.run, data["id"], 0.01)
        errors = []
        ready = threading.Event()
        def answer_after_poll():
            try:
                ready.wait(5)
                self.answer(data["id"])
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=answer_after_poll)
        thread.start()
        real_sleep = decisions.time.sleep
        def sleep(interval):
            ready.set()
            real_sleep(interval)
        try:
            with mock.patch.object(decisions, "POLL_INTERVAL_S", 0.01), mock.patch.object(decisions.time, "sleep", sleep):
                result = decisions.wait(self.run, data["id"], 5)
        finally:
            thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(result, self.derive()["decisions"][data["id"]])
        self.assertEqual(decisions.wait(self.run, data["id"], 0), result)

    def test_open_decisions_order_filter_answered_and_stale(self):
        free = self.ask()
        a = self.ask(node="a")
        b = self.ask(node="b")
        answered = self.ask(node="a")
        self.answer(answered["id"])
        derived = self.derive()
        derived["decisions"] = dict(reversed(list(derived["decisions"].items())))
        self.assertEqual([d["id"] for d in decisions.open_decisions(derived)], [free["id"], a["id"], b["id"]])
        self.assertEqual([d["id"] for d in decisions.open_decisions(derived, "a")], [a["id"]])
        self.assertEqual(decisions.open_decisions(derived, "missing"), [])
        self.event("node.reopen", node="a", reason="retry")
        self.assertEqual([d["id"] for d in decisions.open_decisions(self.derive())], [free["id"], b["id"]])


if __name__ == "__main__":
    unittest.main()
