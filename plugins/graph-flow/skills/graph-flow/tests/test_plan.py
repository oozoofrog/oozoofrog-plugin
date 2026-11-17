import copy
import json
import pathlib
import re
import sys
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from graphflow import core, plan  # noqa: E402


def work(node_id="work", **fields):
    node = {"id": node_id, "kind": "work", "goal": "Do the work",
            "lane": 1, "grade": "scoped", "owns": [node_id + ".py"],
            "checks": [{"id": "unit", "type": "cmd", "run": "true"}]}
    node.update(fields)
    return node


def review(target="work", **fields):
    node = {"id": "review-" + target, "kind": "review", "goal": "Refute the work",
            "target": target, "lens": "correctness", "grade": "daily", "lane": 1,
            "checks": [{"id": "cites", "type": "cites"}]}
    node.update(fields)
    return node


def decision(**fields):
    node = {"id": "approve", "kind": "decision", "goal": "Approve the action",
            "lane": 3, "question": "Proceed?", "decision_kind": "authorization"}
    node.update(fields)
    return node


def document(*nodes):
    return {"schema_version": 1, "goal": "Complete the task", "nodes": list(nodes)}


class PlanTests(unittest.TestCase):
    def assertProblem(self, value, code, node):
        problems = plan.validate(value)
        self.assertTrue(any(p["code"] == code and p["node"] == node for p in problems), problems)
        for problem in problems:
            self.assertEqual(set(problem), {"code", "node", "message"})
            self.assertIsInstance(problem["message"], str)

    def assertNoCode(self, value, code):
        problems = plan.validate(value)
        self.assertNotIn(code, [p["code"] for p in problems], problems)

    def test_contract_example(self):
        records = (SCRIPTS.parent / "references" / "plan.md").read_text(encoding="utf-8")
        section = records.split("# Plan contract", 1)[1]
        example = json.loads(re.search(r"```json\s*\n(.*?)\n```", section, re.S).group(1))
        self.assertEqual([], plan.validate(example))

    def test_v1_required_fields_and_nearby_valid_plan(self):
        self.assertProblem(document(work(goal=42)), "V1", "work")
        self.assertEqual([], plan.validate(document(work(goal="A valid goal"))))
        for value in (None, [], {}, {"schema_version": 2, "nodes": {}},
                      document(None), document(work(kind="code")),
                      document(work(grade="unknown")), document(work(max_attempts=4)),
                      document(work(max_attempts=True)), document(work(owns=[42])),
                      document(work(checks=[None])), document(work(needs=[False]))):
            with self.subTest(value=value):
                self.assertIn("V1", [p["code"] for p in plan.validate(value)])
        self.assertProblem({"schema_version": True, "goal": "g", "nodes": []}, "V1", None)
        for attempts in (1, 2, 3):
            self.assertEqual([], plan.validate(document(work(max_attempts=attempts))))

    def test_v2_node_ids_and_duplicates(self):
        for node_id in ("Upper", "-start", "", "a" * 65, "a\n", "a/b"):
            with self.subTest(node_id=node_id):
                self.assertProblem(document(work(node_id)), "V2", node_id)
        self.assertProblem(document(work(), work()), "V2", "work")
        self.assertProblem(document(work(id=[])), "V2", None)
        for node_id in ("0", "a.b_c-d", "a" * 64):
            self.assertEqual([], plan.validate(document(work(node_id))))
        self.assertEqual([], plan.validate(document(work("a"), work("b"))))

    def test_v2_check_ids_and_duplicates(self):
        for check_id in ("UPPER", "_first", "", "a" * 65, "a\n", ["bad"]):
            with self.subTest(check_id=check_id):
                self.assertProblem(document(work(checks=[{"id": check_id, "type": "cmd", "run": "true"}])), "V2", "work")
        check = {"id": "same", "type": "cmd", "run": "true"}
        self.assertProblem(document(work(checks=[check, check])), "V2", "work")
        for check_id in ("0", "a.b_c-d", "a" * 64):
            self.assertEqual([], plan.validate(document(work(checks=[dict(check, id=check_id)]))))
        self.assertEqual([], plan.validate(document(work("a", checks=[check]), work("b", checks=[check]))))

    def test_v2_single_scope_and_cites_per_node(self):
        for kind in ("scope", "cites"):
            checks = work()["checks"] + [{"id": "first", "type": kind}]
            node = work(checks=checks) if kind == "scope" else review(checks=checks)
            nodes = [node] if kind == "scope" else [work(), node]
            self.assertEqual([], plan.validate(document(*nodes)))
            node["checks"].append({"id": "second", "type": kind})
            self.assertProblem(document(*nodes), "V2", node["id"])

    def test_v5_review_lane_and_decision_checks(self):
        for lane in (2, 3, None, True, "1", []):
            self.assertProblem(document(work(), review(lane=lane)), "V5", "review-work")
        self.assertEqual([], plan.validate(document(work(), review(lane=1))))
        self.assertProblem(document(decision(checks=[{"id": "human", "type": "human"}])), "V5", "approve")
        self.assertEqual([], plan.validate(document(decision(checks=[]))))
        self.assertProblem(document(work(checks=[]), review()), "V5", "work")

    def test_v5_integration_checks_must_be_commands(self):
        value = document(work())
        value["integration_checks"] = [{"id": "all", "type": "cmd", "run": "true"}]
        self.assertEqual([], plan.validate(value))
        for kind in ("host", "human", "scope", "cites"):
            value["integration_checks"] = [{"id": "all", "type": kind}]
            self.assertProblem(value, "V5", None)

    def test_required_top_level_fields(self):
        for key in ("schema_version", "goal", "nodes"):
            value = document(work())
            del value[key]
            self.assertProblem(value, "V1", None)
        for fields in ({"goal": ""}, {"nodes": []}, {"schema_version": 2}):
            value = document(work())
            value.update(fields)
            self.assertProblem(value, "V1", None)
        self.assertEqual([], plan.validate(document(work())))

    def test_v3_artifacts_and_owned_directory(self):
        producer = work("producer", owns=["src/"], outputs=["summary"])
        for source, artifact in (("missing", "src/a.py"), ("producer", ""),
                                 ("producer", "other.py"), ("producer", "srcx/a.py")):
            with self.subTest(source=source, artifact=artifact):
                consumer = work("consumer", needs=[{"from": source, "artifact": artifact}])
                self.assertProblem(document(producer, consumer), "V3", "consumer")
        for artifact in ("src/a.py", "src/sub/a.py", "src/", "summary"):
            consumer = work("consumer", needs=[{"from": "producer", "artifact": artifact}])
            self.assertEqual([], plan.validate(document(producer, consumer)))
        self.assertEqual([], plan.validate(document(work("a"), work("b", needs=[{"from": "a", "artifact": "a.py"}]))))

    def test_v4_cycles_and_nearby_dag(self):
        a = work("a", needs=[{"from": "b", "artifact": "b.py"}])
        b = work("b", needs=[{"from": "a", "artifact": "a.py"}])
        self.assertProblem(document(a, b), "V4", "a")
        self.assertProblem(document(a, b), "V4", "b")
        self.assertEqual([], plan.validate(document(work("a"), b)))
        self.assertProblem(document(work(needs=[{"from": "work", "artifact": "work.py"}])), "V4", "work")
        self.assertProblem(document(work(needs=[{"from": "review-work", "artifact": "findings"}]),
                                    review(outputs=["findings"])), "V4", "work")

    def test_v5_checks_review_and_decision_requirements(self):
        self.assertProblem(document(work(checks=[])), "V5", "work")
        self.assertEqual([], plan.validate(document(work())))
        self.assertProblem(document(work(checks=[{"id": "unit", "type": "cmd"}])), "V5", "work")
        for missing in ("target", "lens"):
            node = review()
            del node[missing]
            self.assertProblem(document(work(), node), "V5", "review-work")
        self.assertProblem(document(work(), review(target="missing")), "V5", "review-missing")
        self.assertProblem(document(decision(), review(target="approve")), "V5", "review-approve")
        self.assertEqual([], plan.validate(document(work(), review())))
        self.assertProblem(document(decision(question="")), "V5", "approve")
        self.assertProblem(document(decision(decision_kind="invalid")), "V5", "approve")
        for kind in ("direction", "information", "review", "authorization"):
            self.assertEqual([], plan.validate(document(decision(decision_kind=kind))))
        self.assertProblem(document(decision(owns=["x"])), "V1", "approve")
        self.assertProblem(document(decision(checks=[{"id": "scope", "type": "scope"}])), "V5", "approve")
        self.assertProblem(document(work(), review(owns=["x"])), "V1", "review-work")

    def test_v6_lane_rules(self):
        node = work()
        del node["lane"]
        self.assertProblem(document(node), "V6", "work")
        for lane in (0, 4, "1", True, None, []):
            self.assertProblem(document(work(lane=lane)), "V6", "work")
        for lane in (1, 2, 3):
            self.assertEqual([], plan.validate(document(work(lane=lane), review())))

    def test_v7_overlapping_owns_with_dependency_counterexample(self):
        a, b = work("a", owns=["src/"]), work("b", owns=["src/b.py"])
        self.assertProblem(document(a, b), "V7", "b")
        b["needs"] = [{"from": "a", "artifact": "src/a.py"}]
        self.assertEqual([], plan.validate(document(a, b)))
        middle = work("middle", needs=[{"from": "a", "artifact": "src/a.py"}])
        b["needs"] = [{"from": "middle", "artifact": "middle.py"}]
        self.assertEqual([], plan.validate(document(a, middle, b)))
        self.assertEqual([], plan.validate(document(b, middle, a)))

    def test_v8_paths(self):
        for path in ("/tmp/x", "../x", "src/../x", ".git", ".git/config",
                     ".graph-flow", ".graph-flow/runs/"):
            with self.subTest(path=path):
                self.assertProblem(document(work(owns=[path])), "V8", "work")
        for path in ("src/x", "src/", "src/.git/config", ".github/x", ".gitignore", ".graph-flow-other/x", "a..b"):
            self.assertEqual([], plan.validate(document(work(owns=[path]))))
        self.assertProblem(document(work(reads=["../read"])), "V8", "work")
        self.assertProblem(document(work(checks=[{"id": "cmd", "type": "cmd", "run": "true", "cwd": ".git"}])), "V8", "work")
        self.assertEqual([], plan.validate(document(work(checks=[{"id": "cmd", "type": "cmd", "run": "true", "cwd": "."}]))))

    def test_v9_raw_plan_escalation_and_review_counterexamples(self):
        self.assertProblem(document(work(lane=2)), "V9", "work")
        self.assertEqual([], plan.validate(document(work(lane=2), review())))
        self.assertEqual([], plan.validate(document(work(lane=1))))
        node = work(lane=1, checks=[{"id": "scope", "type": "scope"}])
        self.assertProblem(document(node), "V9", "work")
        self.assertEqual([], plan.validate(document(node, review())))
        self.assertProblem(document(work(effective_lane=1, lane=2)), "V9", "work")
        self.assertProblem(document(work(effective_lane=3, lane=1)), "V6", "work")

    def test_all_problems_and_no_mutation(self):
        value = document(work(goal=17, owns=["../x"], lane=4,
                              checks=[{"id": "Bad", "type": "cmd"}]), work("other", lane=2))
        original = copy.deepcopy(value)
        problems = plan.validate(value)
        self.assertEqual(original, value)
        self.assertTrue({"V1", "V2", "V5", "V6", "V8", "V9"}.issubset({p["code"] for p in problems}))
        raw = document(work(checks=[]))
        original = copy.deepcopy(raw)
        self.assertProblem(raw, "V5", "work")
        self.assertProblem(raw, "V9", "work")
        self.assertEqual(original, raw)

    def test_malformed_structures_never_raise(self):
        values = (None, False, 1, "bad", [], {})
        for bad in values:
            for field in ("id", "kind", "goal", "needs", "owns", "outputs", "reads", "checks", "lane", "grade", "max_attempts"):
                with self.subTest(bad=bad, field=field):
                    plan.validate(document(work(**{field: bad}), work("other")))
            for key in ("from", "artifact"):
                plan.validate(document(work(needs=[{key: bad}])))
            for key in ("id", "type", "run", "cwd", "timeout_s"):
                plan.validate(document(work(checks=[dict({"id": "unit", "type": "cmd", "run": "true"}, **{key: bad})])))

    def test_check_types_and_fields(self):
        checks = [{"id": "cmd", "type": "cmd", "run": "true", "timeout_s": 0.5},
                  {"id": "scope", "type": "scope"}, {"id": "extra", "type": "cmd", "run": "true"},
                  {"id": "host", "type": "host", "tool": "IDE", "expect": "all tests pass"},
                  {"id": "human", "type": "human", "prompt": "Inspect the rendering"}]
        self.assertEqual([], plan.validate(document(work(checks=checks))))
        for check in ({"id": "unknown", "type": "other"},
                      {"id": "host", "type": "host", "tool": "IDE"},
                      {"id": "host", "type": "host", "expect": "pass"},
                      {"id": "human", "type": "human", "prompt": 1}):
            self.assertProblem(document(work(checks=[checks[0], check])), "V1", "work")
        for timeout in (0, -1, True, "600"):
            self.assertProblem(document(work(checks=[dict(checks[0], timeout_s=timeout)])), "V1", "work")
        value = document(work())
        value["integration_checks"] = [{"id": "all", "type": "cmd"}]
        self.assertProblem(value, "V5", None)
        value["integration_checks"][0]["run"] = "true"
        self.assertEqual([], plan.validate(value))
        value["integration_checks"].append(dict(value["integration_checks"][0]))
        self.assertProblem(value, "V2", None)


class NormalizeTests(unittest.TestCase):
    def test_no_title_is_only_a_notice_for_every_node_kind(self):
        value = document(work(checks=[{"id": "test", "type": "cmd", "run": "test -f guide.txt"}]), review(), decision())
        normalized, notices = plan.normalize(value)
        self.assertEqual([], plan.validate(value))
        self.assertEqual([("no_title", n["id"]) for n in value["nodes"]],
                         [(n["code"], n["node"]) for n in notices])
        for notice in notices:
            self.assertEqual(set(notice), {"code", "node", "message"})
            self.assertTrue(notice["message"])
        titled = copy.deepcopy(value)
        for node in titled["nodes"]:
            node["title"] = "사람이 읽는 제목"
        titled, notices = plan.normalize(titled)
        self.assertEqual([], notices)
        for bare, named in zip(normalized["nodes"], titled["nodes"]):
            self.assertEqual(bare["effective_lane"], named["effective_lane"])
            self.assertEqual(bare["checks"], named["checks"])

    def test_pure_idempotent_defaults_and_unknown_fields(self):
        value = document(work(checks=[{"id": "scope", "type": "scope", "extra": [1]}]), review(), decision())
        value["extension"] = {"future": [1]}
        value["nodes"][0]["extension"] = {"future": [2]}
        original = copy.deepcopy(value)
        normalized, notices = plan.normalize(value)
        self.assertEqual(original, value)
        self.assertEqual(normalized, plan.normalize(normalized)[0])
        self.assertEqual([{"id": "scope", "type": "scope", "extra": [1]}, {"id": "human", "type": "human"}], normalized["nodes"][0]["checks"])
        self.assertEqual([2, 1, 3], [n["effective_lane"] for n in normalized["nodes"]])
        self.assertEqual([("no_machine_check", "work"), ("no_title", "work"),
                          ("no_title", "review-work"), ("no_title", "approve")],
                         [(n["code"], n["node"]) for n in notices])
        for node in normalized["nodes"]:
            for key in ("needs", "owns", "outputs", "reads", "checks"):
                self.assertIsInstance(node[key], list)
            self.assertEqual(None if node["kind"] == "decision" else 3, node.get("max_attempts"))
        self.assertEqual(value["extension"], normalized["extension"])
        self.assertEqual(value["nodes"][0]["extension"], normalized["nodes"][0]["extension"])
        normalized["extension"]["future"].append(9)
        normalized["nodes"][0]["checks"][0]["extra"].append(9)
        self.assertEqual(original, value)

    def test_cmd_work_does_not_escalate_and_resets_effective_lane(self):
        value = document(work(effective_lane=3, max_attempts=1))
        normalized, notices = plan.normalize(value)
        self.assertEqual(1, normalized["nodes"][0]["effective_lane"])
        self.assertEqual(1, normalized["nodes"][0]["max_attempts"])
        self.assertEqual(value["nodes"][0]["checks"], normalized["nodes"][0]["checks"])
        self.assertEqual(["no_title", "unfalsifiable_check"], [n["code"] for n in notices])

    def test_escalates_scope_cites_host_or_empty_checks_and_caps_at_three(self):
        for kind in ("scope", "cites", "host", None):
            for lane in (1, 2, 3):
                with self.subTest(kind=kind, lane=lane):
                    checks = [{"id": "check", "type": kind}] if kind else []
                    normalized, notices = plan.normalize(document(work(lane=lane, checks=checks)))
                    self.assertEqual(min(3, lane + 1), normalized["nodes"][0]["effective_lane"])
                    self.assertEqual("human", normalized["nodes"][0]["checks"][-1]["type"])
                    self.assertEqual("no_machine_check", notices[0]["code"])
                    self.assertEqual(normalized, plan.normalize(normalized)[0])
        node = work()
        del node["checks"]
        normalized, _ = plan.normalize(document(node))
        self.assertEqual([{"id": "human", "type": "human"}], normalized["nodes"][0]["checks"])

    def test_existing_human_and_human_id_collision(self):
        for checks in ([{"id": "custom", "type": "human"}],
                       [{"id": "human", "type": "human"}],
                       [{"id": "human", "type": "scope"}]):
            normalized, _ = plan.normalize(document(work(checks=checks)))
            result = normalized["nodes"][0]["checks"]
            if checks[0]["type"] == "human":
                self.assertEqual(checks, result)
            else:
                self.assertEqual({"id": "human_review", "type": "human"}, result[-1])
            self.assertEqual(normalized, plan.normalize(normalized)[0])

    def test_human_id_sequence_skips_taken_ids(self):
        checks = [{"id": "human", "type": "scope"},
                  {"id": "human_review", "type": "host", "tool": "IDE", "expect": "pass"}]
        for expected in ("human_review_2", "human_review_3", "human_review_4"):
            normalized, notices = plan.normalize(document(work(checks=checks), review()))
            self.assertEqual({"id": expected, "type": "human"}, normalized["nodes"][0]["checks"][-1])
            self.assertEqual(normalized, plan.normalize(normalized)[0])
            self.assertEqual([], plan.validate(document(work(checks=checks), review())))
            self.assertEqual([], plan.validate(normalized))
            self.assertEqual({"code", "node", "message"}, set(notices[0]))
            checks.append({"id": expected, "type": "host", "tool": "IDE", "expect": "pass"})


class PresentationTests(unittest.TestCase):
    def fixture(self):
        checks = [{"id": "cmd", "type": "cmd", "run": "true"},
                  {"id": "scope", "type": "scope"}, {"id": "extra", "type": "cmd", "run": "true"},
                  {"id": "host", "type": "host", "tool": "IDE", "expect": "pass"},
                  {"id": "person", "type": "human"}]
        value = document(work(checks=checks), review(), decision(
            needs=[{"from": "work", "artifact": "work.py"}]))
        value["integration_checks"] = [{"id": "all", "type": "cmd", "run": "true"}]
        return value

    def at(self, value, path):
        for key in path:
            value = value[key]
        return value

    def test_optional_strings_boundaries_types_and_empty_values(self):
        fields = [((), "title", 80, None),
                  (("nodes", 2, "needs", 0), "label", 60, "approve"),
                  (("integration_checks", 0), "title", 120, None)]
        for index, nid in enumerate(("work", "review-work", "approve")):
            fields.extend([(("nodes", index), "title", 60, nid),
                           (("nodes", index), "summary", 300, nid)])
        for index in range(5):
            fields.append((("nodes", 0, "checks", index), "title", 120, "work"))
        for path, key, limit, nid in fields:
            for text in ("사람을 위한 설명", "글" * limit):
                value = self.fixture()
                self.at(value, path)[key] = text
                self.assertEqual([], plan.validate(value), (path, key))
                self.assertEqual(text, self.at(plan.normalize(value)[0], path)[key])
            for bad in (None, 1, True, [], {}, "", " \n", "글" * (limit + 1)):
                with self.subTest(path=path, key=key, bad=bad):
                    value = self.fixture()
                    self.at(value, path)[key] = bad
                    self.assertTrue(any(p["code"] == "V1" and p["node"] == nid
                                        for p in plan.validate(value)))

    def test_context_optional_keys_and_invalid_objects(self):
        for path, nid in ((("nodes", 2), "approve"), (("nodes", 0, "checks", 4), "work")):
            for context in ({}, {k: "이 결정을 설명합니다" for k in
                                ("why", "if_approved", "if_rejected", "undo")}):
                value = self.fixture()
                self.at(value, path)["context"] = context
                self.assertEqual([], plan.validate(value))
            for bad in (None, "why", [], 1, True, {"unknown": "text"}):
                value = self.fixture()
                self.at(value, path)["context"] = bad
                self.assertTrue(any(p["code"] == "V1" and p["node"] == nid
                                    for p in plan.validate(value)))
            for key in ("why", "if_approved", "if_rejected", "undo"):
                value = self.fixture()
                self.at(value, path)["context"] = {key: "글" * 300}
                self.assertEqual([], plan.validate(value))
                for bad in (None, 1, True, [], {}, "", " \n", "글" * 301):
                    with self.subTest(path=path, key=key, bad=bad):
                        self.at(value, path)["context"] = {key: bad}
                        self.assertTrue(any(p["code"] == "V1" and p["node"] == nid
                                            for p in plan.validate(value)))


class QueryTests(unittest.TestCase):
    def test_overlap_path_boundaries(self):
        for a, b in (("src/a", "src/a"), ("src/", "src/a"),
                     ("src/", "src/sub/"), ("src/", "src/")):
            self.assertTrue(plan.overlaps([a], [b]), (a, b))
            self.assertTrue(plan.overlaps([b], [a]), (a, b))
        for a, b in (("src/a", "src/b"), ("src/a", "src/ab"),
                     ("src/", "src-other/a"), ("src/a", "src/a/child")):
            self.assertFalse(plan.overlaps([a], [b]), (a, b))
            self.assertFalse(plan.overlaps([b], [a]), (a, b))
        self.assertFalse(plan.overlaps([], ["src/"]))
        self.assertTrue(plan.overlaps(["other", "src/"], ["else", "src/a"]))

    def test_depends_direct_transitive_review_and_unrelated(self):
        value = document(work("a"), work("b", needs=[{"from": "a", "artifact": "a.py"}]),
                         work("c", needs=[{"from": "b", "artifact": "b.py"}]),
                         review("c"), work("unrelated"))
        self.assertTrue(plan.depends(value, "b", "a"))
        self.assertTrue(plan.depends(value, "c", "a"))
        self.assertTrue(plan.depends(value, "review-c", "c"))
        self.assertTrue(plan.depends(value, "review-c", "a"))
        self.assertFalse(plan.depends(value, "a", "c"))
        self.assertFalse(plan.depends(value, "c", "unrelated"))
        self.assertFalse(plan.depends(value, "c", "c"))
        self.assertFalse(plan.depends(value, "missing", "a"))
        value["nodes"][0]["needs"] = [{"from": "c", "artifact": "c.py"}]
        self.assertFalse(plan.depends(value, "c", "c"))
        self.assertFalse(plan.depends(value, "c", "unrelated"))

    def test_node_by_id_and_error(self):
        node = work()
        self.assertIs(node, plan.node_by_id(document(node), "work"))
        with self.assertRaises(core.GFError) as caught:
            plan.node_by_id(document(node), "missing")
        self.assertEqual("unknown_node", caught.exception.code)
        self.assertEqual(core.EXIT_STATE, caught.exception.exit_code)


if __name__ == "__main__":
    unittest.main()
