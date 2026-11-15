"""Workflow contract checks; runtime tests need only an optional Node executable."""
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import unittest


SKILL = Path(__file__).resolve().parents[1]
AGENTS = SKILL.parents[1] / "agents"
SOURCE = (SKILL / "workflow.js").read_text(encoding="utf-8")
NODE = shutil.which("node")
sys.path.insert(0, str(SKILL / "scripts"))
from graphflow import cli


def metadata():
    prefix = "export const meta = "
    if not SOURCE.startswith(prefix + "{"):
        raise AssertionError("Workflow must begin with export const meta = {")
    # JSON is a strict subset of pure JS literals; calls/computed values cannot pass.
    return json.JSONDecoder().raw_decode(SOURCE[len(prefix):])[0]


HARNESS = r"""
const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const body = input.source.replace(/^export const meta = /, 'const meta = ');
const execute = new AsyncFunction('args', 'agent', 'parallel', 'pipeline', 'phase', body);
(async () => {
  const outputs = [];
  for (const test of input.cases) {
    const calls = [], phases = [];
    let active = 0, maxActive = 0, parallelCalls = 0;
    const agent = async (prompt, options) => {
      const index = calls.length;
      calls.push({prompt, options});
      active++;
      maxActive = Math.max(maxActive, active);
      await Promise.resolve();
      active--;
      const reply = test.replies ? test.replies[index] : {reported: true, summary: 'submission recorded'};
      if (reply && reply.throw) throw new Error(reply.throw);
      return reply;
    };
    const parallel = async tasks => {
      parallelCalls++;
      return Promise.all(tasks.map(task => task()));
    };
    const pipeline = async tasks => {
      let value;
      for (const task of tasks) value = await task(value);
      return value;
    };
    try {
      const result = await execute(test.args, agent, parallel, pipeline, title => phases.push(title));
      outputs.push({result, calls, phases, maxActive, parallelCalls});
    } catch (error) {
      outputs.push({error: error.message, calls, phases, maxActive, parallelCalls});
    }
  }
  process.stdout.write(JSON.stringify(outputs));
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


def arguments():
    return {
        "project": "/test/project with spaces",
        "run": "/test/project with spaces/.graph-flow/runs/build",
        "gf": "/test/plugin's tools/gf",
        "nodes": [
            {"id": "work-a", "brief": "Implement 독립 unit A.\nKeep this exact brief.",
             "model": "routed-model-a", "effort": "routed-effort-a", "kind": "work"},
            {"id": "work-b", "brief": "Implement independent unit B.",
             "model": "routed-model-b", "effort": "routed-effort-b", "kind": "work"},
            {"id": "review-c", "brief": "Review target C through the data-loss lens.",
             "model": "routed-model-c", "effort": "routed-effort-c", "kind": "review"},
        ],
    }


class WorkflowStaticTests(unittest.TestCase):
    def test_literal_metadata_and_declared_phases(self):
        meta = metadata()
        self.assertEqual(meta["name"], "graph-flow")
        self.assertIsInstance(meta["description"], str)
        self.assertTrue(meta["description"].strip())
        self.assertIsInstance(meta["phases"], list)
        titles = {phase["title"] for phase in meta["phases"]}
        used = set(re.findall(r"\bphase\(\s*['\"]([^'\"]+)['\"]", SOURCE))
        used.update(re.findall(r"\bphase:\s*['\"]([^'\"]+)['\"]", SOURCE))
        self.assertTrue(used)
        self.assertFalse(used - titles, "Undeclared phase titles")

    def test_models_are_routed_and_args_are_validated(self):
        self.assertNotRegex(SOURCE, r"(?i)\b(?:claude-[\w.-]+|gpt-[\w.-]+|haiku|sonnet|opus|fable)\b")
        self.assertNotRegex(SOURCE, r"\b(?:model|effort):\s*['\"]")
        self.assertIn("model: node.model", SOURCE)
        self.assertIn("effort: node.effort", SOURCE)
        for field in ("project", "run", "gf", "nodes", "id", "brief", "model", "effort", "kind"):
            self.assertIn(field, SOURCE)
        self.assertIn("typeof args", SOURCE)
        self.assertIn("throw new Error", SOURCE)
        self.assertLess(SOURCE.index("requireArg("), SOURCE.index("await agent("))

    def test_agent_frontmatter_and_documented_commands(self):
        for name in ("gf-splitter", "gf-reviewer"):
            with self.subTest(agent=name):
                document = (AGENTS / (name + ".md")).read_text(encoding="utf-8")
                match = re.match(r"\A---\n(.*?)\n---\n", document, re.DOTALL)
                self.assertIsNotNone(match, "Missing YAML frontmatter")
                fields = {}
                for line in match.group(1).splitlines():
                    key, separator, value = line.partition(": ")
                    self.assertTrue(separator, "Use plain scalar frontmatter fields")
                    self.assertNotIn(key, fields)
                    self.assertTrue(value.strip())
                    fields[key] = value
                self.assertEqual(fields["name"], name)
                self.assertTrue(fields["description"])
                self.assertNotRegex(fields["description"], r":\s|\s#")
                tools = {tool.strip() for tool in fields["tools"].split(",")}
                self.assertEqual(tools, {"Read", "Grep", "Glob", "Bash"})
                self.assertNotIn("model", fields, "The leader routes the model")
                for command in re.findall(r"`gf ([^`]+)`", document):
                    # Parse only: never execute a command or touch a real run.
                    cli._parser().parse_args(shlex.split(command))


@unittest.skipUnless(NODE, "Node is absent from PATH; skipping Workflow runtime stub tests (part b)")
class WorkflowRuntimeTests(unittest.TestCase):
    def run_cases(self, cases):
        result = subprocess.run(
            [NODE, "-e", HARNESS],
            input=json.dumps({"source": SOURCE, "cases": cases}),
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_fanout_prompts_routing_and_cli(self):
        args = arguments()
        outcome = self.run_cases([{"args": args}])[0]
        self.assertNotIn("error", outcome)
        self.assertEqual(len(outcome["calls"]), len(args["nodes"]))
        self.assertEqual(outcome["maxActive"], len(args["nodes"]))
        self.assertEqual(outcome["parallelCalls"], 1)
        self.assertEqual(outcome["phases"], [phase["title"] for phase in metadata()["phases"]])
        self.assertEqual(outcome["result"], [
            {"id": node["id"], "reported": True, "summary": "submission recorded"}
            for node in args["nodes"]
        ])
        for node, call in zip(args["nodes"], outcome["calls"]):
            prompt, options = call["prompt"], call["options"]
            self.assertIn(node["brief"], prompt)
            self.assertEqual(options["model"], node["model"])
            self.assertEqual(options["effort"], node["effort"])
            env = {}
            for line in prompt.splitlines():
                if line.startswith("export GF_"):
                    key, value = shlex.split(line)[1].split("=", 1)
                    env[key] = value
            self.assertEqual(env, {"GF_RUN": args["run"], "GF_NODE": node["id"],
                                   "GF_ROLE": "reviewer" if node["kind"] == "review" else "worker"})
            paths = []
            for line in prompt.splitlines():
                if line.startswith("python3 "):
                    tokens = shlex.split(line)
                    self.assertEqual(tokens[1], args["gf"])
                    values = {"$GF_VERDICT": "fail", "$GF_RESULT": "passed"}
                    parsed = cli._parser().parse_args([values.get(token, token) for token in tokens[2:]])
                    self.assertEqual(parsed.target_node, node["id"])
                    self.assertIn(env["GF_ROLE"], cli.COMMANDS[parsed.command_path]["roles"])
                    paths.append(parsed.command_path)
            self.assertIn(("start",), paths)
            if node["kind"] == "review":
                self.assertEqual(paths, [("start",), ("review", "submit")])
                self.assertEqual(options["agentType"], "graph-flow:gf-reviewer")
                self.assertNotIn("isolation", options)
            else:
                self.assertEqual(paths, [("start",), ("check", "run"), ("check", "record"), ("submit",)])
                self.assertEqual(options["isolation"], "worktree")

    def test_malformed_args_fail_before_any_agent(self):
        bad = [{}, {"args": None}, {"args": []}, {"args": "wrong"}]
        for field in ("project", "run", "gf", "nodes"):
            value = arguments()
            del value[field]
            bad.append({"args": value})
        for field in ("project", "run", "gf"):
            for invalid in ("relative/path", "", 42, "/bad\0path", "/bad\npath"):
                value = arguments()
                value[field] = invalid
                bad.append({"args": value})
        for invalid in ([], {}, None, [None]):
            value = arguments()
            value["nodes"] = invalid
            bad.append({"args": value})
        for field in ("id", "brief", "model", "effort", "kind"):
            for invalid in (None, "", "  ", 42):
                value = arguments()
                value["nodes"][-1][field] = invalid
                bad.append({"args": value})
            value = arguments()
            del value["nodes"][-1][field]
            bad.append({"args": value})
        for field, invalid in (("kind", "decision"), ("id", "../escape"), ("id", "node\n"),
                               ("id", "A"), ("id", "a" * 65), ("id", "work-a")):
            value = arguments()
            value["nodes"][-1][field] = invalid
            bad.append({"args": value})
        for case, outcome in zip(bad, self.run_cases(bad)):
            with self.subTest(case=case):
                self.assertIn("graph-flow Workflow:", outcome.get("error", ""))
                self.assertEqual(outcome["calls"], [])
                self.assertEqual(outcome["parallelCalls"], 0)

    def test_failed_skipped_and_invalid_agent_results_are_not_verdicts(self):
        cases = []
        for reply in (None, {"throw": "host unavailable"}, {"reported": "true", "summary": "bad"},
                      {"reported": True}, {"reported": False, "summary": "blocked"}):
            cases.append({"args": arguments(), "replies": [reply, {"reported": True, "summary": "submission 9"},
                                                           {"reported": True, "summary": "VERDICT fail; submission 10"}]})
        for outcome in self.run_cases(cases):
            self.assertNotIn("error", outcome)
            self.assertEqual(len(outcome["calls"]), 3)
            self.assertEqual(len(outcome["result"]), 3)
            self.assertFalse(outcome["result"][0]["reported"])
            self.assertTrue(outcome["result"][1]["reported"])
            self.assertTrue(outcome["result"][2]["reported"], "A recorded failing review is still reported")
            for result in outcome["result"]:
                self.assertEqual(set(result), {"id", "reported", "summary"})
                self.assertTrue(result["summary"])


if __name__ == "__main__":
    unittest.main()
