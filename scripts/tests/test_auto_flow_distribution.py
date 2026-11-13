"""Package contracts and mocked Workflow behavior; no live agent resolution claims."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from test_document_links import local_targets
from test_plugin_distribution import tree_files

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins/auto-flow"
SKILL = PLUGIN / "skills/auto-flow"


class AutoFlowDistributionTests(unittest.TestCase):
    def test_package_is_complete_and_portable(self):
        expected = {"SKILL.md", "workflow.js", "pick-provider.py", "agents/openai.yaml"}
        self.assertEqual(expected, set(tree_files(SKILL)))
        self.assertEqual(
            {".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
             "agents/flow-planner.md", "agents/flow-verifier.md"}
            | {f"skills/auto-flow/{path}" for path in expected},
            set(tree_files(PLUGIN)),
        )
        for path in PLUGIN.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("/Users/", text, path)
                self.assertNotRegex(text, r"codex-[A-Za-z0-9_-]+", path)
                if path.suffix == ".md":
                    for target in local_targets(text):
                        self.assertTrue((path.parent / target).is_file(), (path, target))
        for name in ("flow-planner", "flow-verifier"):
            self.assertIn(f"name: {name}\n", (PLUGIN / f"agents/{name}.md").read_text())

    def test_discovery_metadata_and_documentation_agree(self):
        description = (SKILL / "SKILL.md").read_text().split("description: ", 1)[1].splitlines()[0]
        metadata = dict(line.strip().split(": ", 1) for line in
                        (SKILL / "agents/openai.yaml").read_text().splitlines()[1:])
        metadata = {key: json.loads(value) for key, value in metadata.items()}
        codex = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
        self.assertEqual("0.2.0", codex["version"])
        self.assertEqual("./skills/", codex["skills"])
        self.assertEqual(description, codex["description"])
        self.assertEqual(description, codex["interface"]["longDescription"])
        for yaml_key, json_key in (("display_name", "displayName"),
                                  ("short_description", "shortDescription")):
            self.assertEqual(metadata[yaml_key], codex["interface"][json_key])
        self.assertTrue(25 <= len(metadata["short_description"]) <= 64)
        self.assertEqual([metadata["default_prompt"]], codex["interface"]["defaultPrompt"])
        self.assertIn("$auto-flow", metadata["default_prompt"])
        for key in ("mcpServers", "hooks", "apps", "agents"):
            self.assertNotIn(key, codex)
        for name in ("README.md", "README.ko.md"):
            self.assertIn(description, (ROOT / name).read_text())
            self.assertIn("docs/plugin-installation.md#auto-flow", (ROOT / name).read_text())
        for name in ("docs/plugin-installation.md", "CHANGELOG.md"):
            self.assertIn("auto-flow", (ROOT / name).read_text())

    @unittest.skipUnless(shutil.which("node"), "Node is needed for mocked Workflow execution")
    def test_workflow_fallbacks_preserve_options_logs_and_run_cap(self):
        # Execute the whole Workflow with stub agents, including a fix and re-verify.
        harness = r"""
const assert = require('node:assert/strict')
const fs = require('node:fs')
const source = fs.readFileSync(process.argv[1], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const workflow = new AsyncFunction('args', 'agent', 'phase', 'log', 'parallel', source)
;(async () => {
  for (const mode of ['namespaced', 'bare', 'default', 'cap']) {
    const calls = [], logs = []
    const agent = async (prompt, opts) => {
      calls.push(opts)
      if (opts.agentType === 'Explore' && mode === 'cap') throw Error('unavailable')
      if (opts.agentType && opts.agentType !== 'Explore') {
        const accepted = mode === 'namespaced' ? opts.agentType.startsWith('auto-flow:')
          : mode === 'bare' && !opts.agentType.startsWith('auto-flow:')
        if (!accepted) throw Error('unavailable')
      }
      if (opts.phase === 'Explore') return 'code map'
      if (opts.phase === 'Plan') return { contracts: '', risks: [], indivisible: false,
        units: Array.from({ length: 4 }, (_, i) => ({ id: `u${i+1}`, goal: 'unit',
          files: [], acceptance: '', checks: '', tier: 'scoped' })) }
      if (opts.phase === 'Verify' || opts.phase === 'Re-verify') {
        const fail = mode === 'cap' && opts.phase === 'Verify'
        return { overall: fail ? 'fail' : 'pass', units: [
          { id: 'u1', verdict: fail ? 'fail' : 'pass', kind: fail ? 'defect' : 'none', findings: [] }
        ], checksRun: [], integration: '', summary: '' }
      }
      return { status: 'done', summary: '', changedFiles: [], checksRun: [], evidence: '', lowConfidence: [] }
    }
    const result = await workflow({ task: 'test', tier: 'large' }, agent, () => {},
      note => logs.push(note), () => { throw Error('unexpected parallel call') })
    assert.equal(result.outcome, 'pass')
    assert.equal(result.spawned, mode === 'cap' ? 9 : 7)
    assert.equal(result.notes.length, { namespaced: 0, bare: 2, default: 4, cap: 7 }[mode])
    for (const note of result.notes) assert.ok(logs.includes(note))
    assert.ok(!calls.some(opts => opts.agentType === 'auto-flow:Explore'))
    for (const phase of ['Plan', 'Verify', ...(mode === 'cap' ? ['Re-verify'] : [])]) {
      const attempts = calls.filter(opts => opts.phase === phase)
      const name = phase === 'Plan' ? 'flow-planner' : 'flow-verifier'
      const expected = mode === 'namespaced' ? [`auto-flow:${name}`]
        : mode === 'bare' ? [`auto-flow:${name}`, name] : [`auto-flow:${name}`, name, undefined]
      assert.deepEqual(attempts.map(opts => opts.agentType), expected)
      const { agentType, ...first } = attempts[0]
      for (const { agentType, ...rest } of attempts) assert.deepEqual(rest, first)
    }
    if (mode === 'cap') {
      assert.ok(calls.length > 9, 'name retries must not consume the run cap')
      assert.deepEqual(calls.filter(opts => opts.phase === 'Fix').map(opts => [opts.model, opts.effort]),
        [['sonnet', 'high']])
    }
  }
  // null(건너뜀·API 오류)은 다른 이름으로 다시 띄우지 않는다.
  for (const skipped of ['Triage', 'Plan', 'Verify']) {
    const calls = []
    const agent = async (prompt, opts) => {
      calls.push(opts)
      if (opts.phase === skipped) return null
      if (opts.phase === 'Triage') return { tier: 'large', units: [], reason: '' }
      if (opts.phase === 'Explore') return 'code map'
      if (opts.phase === 'Plan') return { contracts: '', risks: [], indivisible: true, units: [] }
      return { status: 'done', summary: '', changedFiles: [], checksRun: [], evidence: '', lowConfidence: [] }
    }
    const result = await workflow({ task: 'test', runId: 20261113231500 }, agent, () => {}, () => {},
      () => { throw Error('unexpected parallel call') })
    assert.equal(result.outcome, 'unknown')
    assert.equal(calls.filter(opts => opts.phase === skipped).length, 1)
    assert.ok(!calls.some(opts => opts.phase === 'Fix'))
    if (skipped !== 'Verify') assert.ok(!calls.some(opts => opts.phase === 'Execute'))
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
"""
        result = subprocess.run(["node", "-e", harness, str(SKILL / "workflow.js")],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
