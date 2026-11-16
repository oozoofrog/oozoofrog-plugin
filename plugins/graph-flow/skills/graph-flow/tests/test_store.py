import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from graphflow import core, store  # noqa: E402

ACTOR = {"role": "leader", "node": None, "session": "test"}


class EnvCase(unittest.TestCase):
    KEYS = ("GF_ROLE", "GF_NODE", "GF_SESSION", "GF_HOME", "T3CODE_THREAD_ID", "CLAUDE_CODE_SESSION_ID")

    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in self.KEYS}
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name).resolve()
        self.home = self.tmp / "home"
        os.environ["GF_HOME"] = str(self.home)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def tearDown(self):
        for k, v in self._saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        self._tmp.cleanup()

    def new_run(self, run_id="r1"):
        return store.init_run(self.repo, run_id, ACTOR)

    def log_lines(self, run_dir):
        return (run_dir / "events.jsonl").read_bytes().split(b"\n")

    def run_helper(self, body, args_list):
        helper = self.tmp / "helper.py"
        helper.write_text("import sys\nsys.path.insert(0, sys.argv[1])\n" + textwrap.dedent(body))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        procs = [subprocess.Popen([sys.executable, "-I", "-S", "-B", str(helper), str(SCRIPTS)] + a,
                                  env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for a in args_list]
        for p in procs:
            out, err = p.communicate(timeout=300)
            self.assertEqual(p.returncode, 0, err.decode())


class InitTests(EnvCase):
    def test_layout_and_registry(self):
        run = self.new_run()
        meta = self.repo / ".graph-flow"
        self.assertEqual(run, meta / "runs" / "r1")
        for sub in ("plans", "evidence", "brief"):
            self.assertTrue((run / sub).is_dir())
        self.assertTrue((run / ".lock").exists())
        lines = (meta / ".gitignore").read_text().splitlines()
        self.assertIn("runs/", lines)
        self.assertIn(".lock", lines)
        evs = store.events(run)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["type"], "run.init")
        self.assertEqual(evs[0]["data"], {"run_id": "r1", "project_root": str(self.repo),
                                          "schema_version": 1})
        reg = json.loads((self.home / "registry.json").read_text())
        self.assertEqual([p["root"] for p in reg["projects"]], [str(self.repo)])
        self.assertRegex(reg["projects"][0]["added"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_second_run_keeps_registry_and_gitignore(self):
        self.new_run("r1")
        self.new_run("r2")
        reg = json.loads((self.home / "registry.json").read_text())
        self.assertEqual(len(reg["projects"]), 1)
        text = (self.repo / ".graph-flow" / ".gitignore").read_text()
        self.assertEqual(text.count("runs/"), 1)

    def test_run_exists(self):
        self.new_run()
        with self.assertRaises(core.GFError) as cm:
            self.new_run()
        self.assertEqual(cm.exception.code, "run_exists")
        self.assertEqual(len(store.events(self.repo / ".graph-flow" / "runs" / "r1")), 1)

    def test_bad_run_id(self):
        for bad in ("", "../x", "A", "a/b"):
            with self.assertRaises(core.GFError):
                store.init_run(self.repo, bad, ACTOR)


class EventTests(EnvCase):
    def test_envelope(self):
        run = self.new_run()
        with store.transaction(run) as tx:
            self.assertEqual(tx.revision, 0)
            self.assertIsNone(tx.plan)
            e2 = tx.append("host.set", {"capabilities": ["workflow"]}, ACTOR)
            e3 = tx.append("node.reopen", {"node": "a", "reason": "x"}, ACTOR)
        evs = store.events(run)
        self.assertEqual([e["seq"] for e in evs], [1, 2, 3])
        self.assertEqual(evs[1:], [e2, e3])
        for e in evs:
            self.assertEqual(set(e), {"seq", "ts", "run", "plan_revision", "actor", "type", "data"})
            self.assertEqual(e["run"], "r1")
            self.assertEqual(e["plan_revision"], 0)
            self.assertEqual(e["actor"], ACTOR)
            self.assertRegex(e["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(evs[1]["data"], {"capabilities": ["workflow"]})

    def test_tx_events_lists_log(self):
        run = self.new_run()
        with store.transaction(run) as tx:
            self.assertEqual([e["type"] for e in tx.events], ["run.init"])

    def test_concurrent_processes(self):
        run = self.new_run()
        body = """
        from graphflow import store
        run, ident = sys.argv[2], sys.argv[3]
        actor = {"role": "leader", "node": None, "session": ident}
        for i in range(200):
            with store.transaction(run) as tx:
                tx.append("host.set", {"w": ident, "i": i}, actor)
        """
        self.run_helper(body, [[str(run), "w%d" % k] for k in range(8)])
        raw = (run / "events.jsonl").read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        lines = raw.split(b"\n")[:-1]
        self.assertEqual(len(lines), 1601)
        parsed = [json.loads(l) for l in lines]
        self.assertEqual([e["seq"] for e in parsed], list(range(1, 1602)))
        per_worker = {}
        for e in parsed[1:]:
            per_worker.setdefault(e["data"]["w"], []).append(e["data"]["i"])
        self.assertEqual(sorted(per_worker), ["w%d" % k for k in range(8)])
        for seqs in per_worker.values():
            self.assertEqual(seqs, list(range(200)))

    def test_raise_appends_nothing(self):
        run = self.new_run()
        before = (run / "events.jsonl").read_bytes()
        with self.assertRaises(RuntimeError):
            with store.transaction(run) as tx:
                tx.append("host.set", {"capabilities": []}, ACTOR)
                raise RuntimeError("boom")
        self.assertEqual((run / "events.jsonl").read_bytes(), before)

    def test_transactions_do_not_interleave(self):
        run = self.new_run()
        entered = threading.Event()
        marks = {}

        def first():
            with store.transaction(run) as tx:
                entered.set()
                time.sleep(0.4)
                tx.append("host.set", {"who": "first"}, ACTOR)
                marks["first_left"] = time.monotonic()

        t = threading.Thread(target=first)
        t.start()
        self.assertTrue(entered.wait(10))
        with store.transaction(run) as tx:
            marks["second_entered"] = time.monotonic()
            self.assertEqual(tx.events[-1]["data"], {"who": "first"})
            ev = tx.append("host.set", {"who": "second"}, ACTOR)
        t.join()
        self.assertGreaterEqual(marks["second_entered"], marks["first_left"])
        self.assertEqual(ev["seq"], 3)

    def test_lock_timeout(self):
        run = self.new_run()
        with store.locked(run / ".lock"):
            t0 = time.monotonic()
            with self.assertRaises(core.GFError) as cm:
                with store.locked(run / ".lock", timeout_s=0.05):
                    pass
            self.assertLess(time.monotonic() - t0, 5)
            self.assertEqual(cm.exception.code, "lock_timeout")
            self.assertEqual(cm.exception.exit_code, core.EXIT_IO)
            with self.assertRaises(core.GFError) as cm:
                with store.transaction(run, timeout_s=0.05):
                    pass
            self.assertEqual(cm.exception.code, "lock_timeout")
        with store.locked(run / ".lock", timeout_s=0.05):
            pass

    def test_incomplete_tail(self):
        run = self.new_run()
        log = run / "events.jsonl"
        garbage = b'{"seq": 2, "type": "half'
        with open(str(log), "ab") as f:
            f.write(garbage)
        self.assertEqual(len(store.events(run)), 1)
        with store.transaction(run) as tx:
            ev = tx.append("host.set", {"capabilities": []}, ACTOR)
        self.assertEqual(ev["seq"], 3)
        raw = log.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn(garbage, raw)
        parsed = [json.loads(l) for l in raw.split(b"\n")[:-1]]
        self.assertEqual([e["type"] for e in parsed], ["run.init", "log.recovered", "host.set"])
        self.assertEqual(parsed[1]["data"], {"dropped_bytes": len(garbage)})
        self.assertEqual([e["seq"] for e in parsed], [1, 2, 3])

    def test_unparsable_last_line_with_newline(self):
        run = self.new_run()
        with open(str(run / "events.jsonl"), "ab") as f:
            f.write(b"not json\n")
        self.assertEqual(len(store.events(run)), 1)
        with store.transaction(run) as tx:
            tx.append("host.set", {}, ACTOR)
        evs = store.events(run)
        self.assertEqual([e["type"] for e in evs], ["run.init", "log.recovered", "host.set"])
        self.assertEqual(evs[1]["data"]["dropped_bytes"], 9)

    def test_tail_kept_when_tx_raises(self):
        run = self.new_run()
        with open(str(run / "events.jsonl"), "ab") as f:
            f.write(b"{")
        with self.assertRaises(RuntimeError):
            with store.transaction(run) as tx:
                tx.append("host.set", {}, ACTOR)
                raise RuntimeError()
        self.assertTrue((run / "events.jsonl").read_bytes().endswith(b"{"))

    def test_corrupt_middle_line(self):
        run = self.new_run()
        with open(str(run / "events.jsonl"), "ab") as f:
            f.write(b"oops\n")
        with store.transaction(run) as tx:
            tx.append("host.set", {}, ACTOR)
        with open(str(run / "events.jsonl"), "r+b") as f:
            data = f.read()
            f.seek(0)
            f.write(data.replace(b'"log.recovered"', b'"log.recovered'))
        with self.assertRaises(core.GFError) as cm:
            store.events(run)
        self.assertEqual(cm.exception.exit_code, core.EXIT_IO)


class PlanTests(EnvCase):
    def test_write_plan_and_read(self):
        run = self.new_run()
        self.assertIsNone(store.read_plan(run))
        plan = {"schema_version": 1, "goal": "g", "nodes": [{"id": "a"}]}
        with store.transaction(run) as tx:
            rev, sha = tx.write_plan(plan)
            ev = tx.append("plan.set", {"revision": rev, "plan_sha256": sha, "fingerprints": {},
                                        "constraints_applied": []}, ACTOR)
            self.assertEqual(tx.revision, 1)
            self.assertEqual(tx.plan, plan)
            after = tx.append("host.set", {}, ACTOR)
        self.assertEqual(rev, 1)
        path = run / "plans" / "0001.json"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), sha)
        self.assertEqual(ev["plan_revision"], 1)
        self.assertEqual(after["plan_revision"], 1)
        self.assertEqual(store.read_plan(run), plan)
        with store.transaction(run) as tx:
            self.assertEqual((tx.revision, tx.plan), (1, plan))

        plan2 = dict(plan, goal="g2")
        with store.transaction(run) as tx:
            rev2, sha2 = tx.write_plan(plan2)
            tx.append("plan.set", {"revision": rev2, "plan_sha256": sha2}, ACTOR)
        self.assertEqual(rev2, 2)
        self.assertEqual(store.read_plan(run), plan2)
        self.assertEqual(json.loads(path.read_text()), plan)

    def test_orphan_plan_file_ignored(self):
        run = self.new_run()
        plan = {"goal": "one"}
        with store.transaction(run) as tx:
            rev, sha = tx.write_plan(plan)
            tx.append("plan.set", {"revision": rev, "plan_sha256": sha}, ACTOR)
        with self.assertRaises(RuntimeError):
            with store.transaction(run) as tx:
                tx.write_plan({"goal": "orphan"})
                raise RuntimeError()
        self.assertTrue((run / "plans" / "0002.json").exists())
        self.assertEqual(store.read_plan(run), plan)
        with store.transaction(run) as tx:
            self.assertEqual((tx.revision, tx.plan), (1, plan))
        (run / "plans" / "0009.json").write_text('{"goal": "stray"}')
        self.assertEqual(store.read_plan(run), plan)

    def test_write_plan_uses_atomic_write(self):
        run = self.new_run()
        calls = []
        real_replace = os.replace
        real_fsync = os.fsync

        def fsync(fd):
            calls.append("fsync")
            return real_fsync(fd)

        def replace(src, dst):
            calls.append(("replace", pathlib.Path(src).parent, pathlib.Path(dst)))
            return real_replace(src, dst)

        with mock.patch.object(store.os, "replace", replace), mock.patch.object(store.os, "fsync", fsync):
            with store.transaction(run) as tx:
                tx.write_plan({"goal": "g"})
        reps = [c for c in calls if isinstance(c, tuple)]
        self.assertEqual(len(reps), 1)
        self.assertEqual(reps[0][1], run / "plans")
        self.assertEqual(reps[0][2], run / "plans" / "0001.json")
        self.assertLess(calls.index("fsync"), calls.index(reps[0]))
        self.assertEqual([p.name for p in (run / "plans").iterdir()], ["0001.json"])

    def test_atomic_write(self):
        p = self.tmp / "sub" / "f.txt"
        store.atomic_write(p, "hello\n")
        self.assertEqual(p.read_text(), "hello\n")
        store.atomic_write(p, b"bytes")
        self.assertEqual(p.read_bytes(), b"bytes")
        self.assertEqual(os.listdir(str(p.parent)), ["f.txt"])


class EvidenceTests(EnvCase):
    def test_unique_paths(self):
        run = self.new_run()
        paths = [store.evidence_path(run, "export", "unit", 2) for _ in range(50)]
        self.assertEqual(len(set(paths)), 50)
        for p in paths:
            self.assertTrue(p.is_file())
            self.assertEqual(p.parent, run / "evidence" / "export" / "unit")
            self.assertRegex(p.name, r"^a2-[0-9a-f]{8}\.log$")
        p = store.evidence_path(run, "_run", "all-tests", 0)
        self.assertEqual(p.parent, run / "evidence" / "_run" / "all-tests")

    def test_bad_names(self):
        run = self.new_run()
        for node, check in (("..", "c"), ("a/b", "c"), ("n", "../x")):
            with self.assertRaises(core.GFError):
                store.evidence_path(run, node, check, 1)


class RegistryTests(EnvCase):
    def test_concurrent_register(self):
        roots = [self.tmp / ("p%d" % k) for k in range(6)]
        for r in roots:
            r.mkdir()
        body = """
        from graphflow import store
        for i in range(10):
            for r in sys.argv[2:]:
                store.register_project(r)
        """
        args = [[str(r) for r in roots[k:] + roots[:k]] for k in range(6)]
        self.run_helper(body, args)
        reg = json.loads((self.home / "registry.json").read_text())
        got = [p["root"] for p in reg["projects"]]
        self.assertEqual(sorted(got), sorted(str(r) for r in roots))

    def test_idempotent(self):
        store.register_project(self.repo)
        store.register_project(str(self.repo) + "/")
        reg = json.loads((self.home / "registry.json").read_text())
        self.assertEqual(len(reg["projects"]), 1)


class ProjectTests(EnvCase):
    def test_project_root(self):
        sub = self.repo / "a" / "b"
        sub.mkdir(parents=True)
        self.assertEqual(store.project_root(sub), self.repo)
        self.assertEqual(store.project_root(self.repo), self.repo)
        cwd = os.getcwd()
        try:
            os.chdir(str(sub))
            self.assertEqual(store.project_root(), self.repo)
        finally:
            os.chdir(cwd)

    def test_outside_repository(self):
        outside = self.tmp / "plain"
        outside.mkdir()
        env = {"GIT_CEILING_DIRECTORIES": str(self.tmp)}
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(core.GFError) as cm:
                store.project_root(outside)
        self.assertEqual(cm.exception.code, "not_a_repository")

    def test_project_of(self):
        run = self.new_run()
        self.assertEqual(store.project_of(run), self.repo)


if __name__ == "__main__":
    unittest.main()
