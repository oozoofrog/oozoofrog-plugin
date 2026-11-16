import pathlib
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from graphflow import core, graph  # noqa: E402


def node(nid, kind="work", needs=(), **extra):
    n = {"id": nid, "kind": kind, "needs": [{"from": f, "artifact": "x"} for f in needs],
         "owns": [], "outputs": [], "reads": [], "checks": [], "lane": 1,
         "effective_lane": 1, "max_attempts": 3}
    n.update(extra)
    return n


def st(status="pending", attempts=0, isolation=None, commit=None, max_attempts=3):
    s = {"status": status, "attempts": attempts, "max_attempts": max_attempts,
         "assignment": {"isolation": isolation} if isolation else None, "submission": None}
    if status in graph.WITH_SUBMISSION or status == "passed":
        s["submission"] = {"id": 5, "commit": commit}
    return s


def state(**nodes):
    return {"nodes": nodes}


class NeedsTests(unittest.TestCase):
    def test_needs_require_passed(self):
        plan = {"nodes": [node("a"), node("b", needs=["a"])]}
        self.assertFalse(graph.needs_satisfied(plan, state(a=st("submitted"), b=st()), "b"))
        self.assertTrue(graph.needs_satisfied(plan, state(a=st("passed"), b=st()), "b"))

    def test_review_needs_only_a_current_submission_of_its_target(self):
        plan = {"nodes": [node("a"), node("v", "review", needs=["a"], target="a", lens="x")]}
        for status, ok in (("running", False), ("submitted", True), ("unverified", True),
                           ("held", True), ("awaiting_approval", True), ("rejected", False),
                           ("passed", False)):
            self.assertEqual(ok, graph.needs_satisfied(plan, state(a=st(status), v=st()), "v"), status)

    def test_review_other_needs_still_require_passed(self):
        plan = {"nodes": [node("a"), node("c"),
                          node("v", "review", needs=["a", "c"], target="a", lens="x")]}
        s = state(a=st("submitted"), c=st("running"), v=st())
        self.assertFalse(graph.needs_satisfied(plan, s, "v"))
        s["nodes"]["c"] = st("passed")
        self.assertTrue(graph.needs_satisfied(plan, s, "v"))

    def test_unknown_node(self):
        with self.assertRaises(core.GFError) as cm:
            graph.needs_satisfied({"nodes": []}, state(), "zz")
        self.assertEqual("unknown_node", cm.exception.code)


class StartTests(unittest.TestCase):
    def test_startable_statuses(self):
        plan = {"nodes": [node("a")]}
        for status in graph.STARTABLE:
            self.assertIsNone(graph.start_problem(plan, state(a=st(status, isolation="worktree")), "a"), status)
        for status in ("running", "submitted", "passed"):
            self.assertEqual("not_startable",
                             graph.start_problem(plan, state(a=st(status, isolation="worktree")), "a"), status)

    def test_exhausted_and_replan(self):
        plan = {"nodes": [node("a")]}
        self.assertEqual("attempts_exhausted",
                         graph.start_problem(plan, state(a=st("rejected", attempts=3)), "a"))
        self.assertEqual("attempts_exhausted",
                         graph.start_problem(plan, state(a=st("replan", attempts=1)), "a"))

    def test_live_work_on_the_last_attempt_is_not_exhausted(self):
        plan = {"nodes": [node("a")]}
        for status in ("running", "submitted", "passed"):
            self.assertEqual(
                "not_startable",
                graph.start_problem(plan, state(a=st(status, attempts=3, isolation="worktree")), "a"),
                status)
        for status in ("rejected", "held", "unverified", "awaiting_approval"):
            self.assertEqual(
                "attempts_exhausted",
                graph.start_problem(plan, state(a=st(status, attempts=3, isolation="worktree")), "a"),
                status)

    def test_decision_never_starts(self):
        plan = {"nodes": [node("d", "decision")]}
        self.assertEqual("not_startable", graph.start_problem(plan, state(d=st()), "d"))

    def test_needs_unsatisfied(self):
        plan = {"nodes": [node("a"), node("b", needs=["a"])]}
        self.assertEqual("needs_unsatisfied", graph.start_problem(plan, state(a=st("running"), b=st()), "b"))

    def test_shared_tree_is_serial(self):
        plan = {"nodes": [node("a"), node("b")]}
        self.assertEqual("shared_busy", graph.start_problem(plan, state(a=st("running"), b=st()), "b"))
        self.assertEqual("shared_busy", graph.start_problem(plan, state(a=st("submitted"), b=st()), "b"))
        self.assertEqual("shared_busy", graph.start_problem(plan, state(a=st("held"), b=st()), "b"))
        self.assertIsNone(graph.start_problem(plan, state(a=st("passed"), b=st()), "b"))
        self.assertIsNone(graph.start_problem(plan, state(a=st("rejected"), b=st()), "b"))

    def test_committed_or_isolated_work_does_not_block(self):
        plan = {"nodes": [node("a"), node("b")]}
        self.assertIsNone(graph.start_problem(plan, state(a=st("submitted", commit="abc"), b=st()), "b"))
        self.assertIsNone(graph.start_problem(
            plan, state(a=st("running", isolation="worktree"), b=st()), "b"))
        self.assertIsNone(graph.start_problem(
            plan, state(a=st("running"), b=st(isolation="worktree")), "b"))

    def test_reviews_neither_block_nor_are_blocked(self):
        plan = {"nodes": [node("a"), node("b"), node("v", "review", needs=["a"], target="a", lens="x")]}
        s = state(a=st("submitted", commit="abc"), b=st("running"), v=st())
        self.assertIsNone(graph.start_problem(plan, s, "v"))
        s = state(a=st("submitted", commit="abc"), b=st(), v=st("running"))
        self.assertIsNone(graph.start_problem(plan, s, "b"))

    def test_check_start_raises_state_error(self):
        plan = {"nodes": [node("a")]}
        with self.assertRaises(core.GFError) as cm:
            graph.check_start(plan, state(a=st("passed")), "a")
        self.assertEqual(("not_startable", core.EXIT_STATE), (cm.exception.code, cm.exception.exit_code))


class ReadyTests(unittest.TestCase):
    def test_plan_order_and_decisions(self):
        plan = {"nodes": [node("a"), node("b", needs=["a"]), node("d", "decision", needs=["a"]),
                          node("c")]}
        s = state(a=st(isolation="worktree"), b=st(), d=st(), c=st(isolation="worktree"))
        self.assertEqual(["a", "c"], graph.ready(plan, s))
        s["nodes"]["a"] = st("passed")
        self.assertEqual(["b", "d", "c"], graph.ready(plan, s))
        s["nodes"]["d"] = st("passed")
        self.assertEqual(["b", "c"], graph.ready(plan, s))

    def test_a_verdict_changes_the_list(self):
        plan = {"nodes": [node("a"), node("b", needs=["a"])]}
        s = state(a=st("submitted", commit="x"), b=st())
        self.assertEqual([], graph.ready(plan, s))
        s["nodes"]["a"] = st("rejected")
        self.assertEqual(["a"], graph.ready(plan, s))
        s["nodes"]["a"] = st("passed")
        self.assertEqual(["b"], graph.ready(plan, s))


if __name__ == "__main__":
    unittest.main()
