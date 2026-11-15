export const meta = {
  "name": "graph-flow",
  "description": "Dispatch assigned graph-flow nodes and collect their reporting acknowledgements",
  "phases": [
    { "title": "Execute", "detail": "One session per assigned node; the leader gates the recorded evidence" }
  ]
}

// args: { project, run, nodes: [{ id, brief, model, effort, kind }], gf }
// Launch from project. Work assignments use host worktrees; reviews use the shared tree.
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value)
const text = value => typeof value === 'string' && value.trim().length > 0 && !value.includes('\0')
function requireArg(condition, message) {
  if (!condition) throw new Error(`graph-flow Workflow: ${message}`)
}
requireArg(typeof args !== 'undefined' && object(args), 'args must be an object')
for (const key of ['project', 'run', 'gf']) {
  requireArg(text(args[key]) && args[key].startsWith('/') && !/[\r\n]/.test(args[key]),
    `args.${key} must be an absolute path`)
}
requireArg(Array.isArray(args.nodes) && args.nodes.length > 0, 'args.nodes must be a nonempty array')
const ids = new Set()
for (const [index, node] of args.nodes.entries()) {
  const field = `args.nodes[${index}]`
  requireArg(object(node), `${field} must be an object`)
  requireArg(text(node.id) && node.id === node.id.trim() && /^[a-z0-9][a-z0-9._-]{0,63}$/.test(node.id),
    `${field}.id must be a valid node id`)
  requireArg(!ids.has(node.id), `${field}.id duplicates ${node.id}`)
  ids.add(node.id)
  for (const key of ['brief', 'model', 'effort']) {
    requireArg(text(node[key]), `${field}.${key} must be a nonempty string`)
  }
  requireArg(node.kind === 'work' || node.kind === 'review', `${field}.kind must be work or review`)
}

const quote = value => "'" + value.replace(/'/g, "'\"'\"'") + "'"
const gf = `python3 ${quote(args.gf)} --json`
const reportSchema = {
  type: 'object',
  properties: { reported: { type: 'boolean' }, summary: { type: 'string' } },
  required: ['reported', 'summary'],
}

function prompt(node) {
  const reviewer = node.kind === 'review'
  const role = reviewer ? 'reviewer' : 'worker'
  const id = quote(node.id)
  const commands = reviewer
    ? `Read the target diff through exactly the brief's one lens. Change no project files.
Write the findings array ({severity, file, line, text}, or []) to a session scratch JSON file outside project source.
Set GF_FINDINGS to that file and GF_VERDICT to pass or fail based on the lens findings, then run:
${gf} review submit ${id} --verdict "$GF_VERDICT" --findings "$GF_FINDINGS"
Return the fixed UNIT / VERDICT / REASON / EVIDENCE / SCOPE report in summary, including the submission id.`
    : `Work only inside the brief's owned paths in the host-created worktree. Preserve existing edits.
For each cmd check in the brief, set GF_CHECK to its check id and run:
${gf} check run ${id} "$GF_CHECK" --cwd "$GF_CWD"
Inspect failures, correct the work, and repeat checks within this attempt. Never weaken the checks.
For each host check, invoke its actual tool, set GF_CHECK, GF_RESULT (passed or failed), and GF_NOTE to observed evidence, then run:
${gf} check record ${id} "$GF_CHECK" --result "$GF_RESULT" --note "$GF_NOTE"
Leave scope and human checks to the leader's gate. Commit only owned changes on the host-assigned worktree branch.
Set GF_COMMIT to the full commit SHA, GF_BRANCH to that branch, and GF_NOTES to the result and evidence, then run:
${gf} submit ${id} --cwd "$GF_CWD" --commit "$GF_COMMIT" --branch "$GF_BRANCH" --notes "$GF_NOTES"
If uncertain, append --low-confidence "specific uncertainty" to that submission command.
Include the submission id, commit, branch, actual commands and exit codes in summary.`
  return `${node.brief}

## Workflow reporting contract
Do the work yourself. Do not start sub-sessions or ask the user anything. Work and report in English.
Project: ${args.project}
Use this binding in every shell invocation; do not rely on exports persisting between tools:
export GF_RUN=${quote(args.run)}
export GF_ROLE=${quote(role)}
export GF_NODE=${id}
GF_SESSION is optional; set it only to your actual session identity, never an invented one.
${reviewer
    ? `cd ${quote(args.project)}\nGF_CWD=${quote(args.project)}`
    : `Keep the host-created worktree as your working directory. Do not cd to the leader's project.
Verify that it is a separate checkout of ${args.project} with the required inputs; otherwise report a blocker before starting.
GF_CWD="$(pwd -P)"`}
Use the absolute entry script above even if the brief abbreviates it. Replace its start/check/submit examples with these cwd-aware commands.
Start exactly once before working:
${gf} start ${id} --cwd "$GF_CWD"
If start fails (including shared_busy), stop this node and return reported: false with the error. Never bypass the guard.
${commands}
Return {reported: true, summary: "..."} only after your own submission command exits 0 with ok: true and a submission id.
On missing evidence, a blocker, or a failed submission return reported: false and explain it. Keep the report at most 20 lines.
Do not assign, merge, gate, revise the plan, answer decisions, or change role/node. The leader decides acceptance from gf records.`
}

phase('Execute')
const results = await parallel(args.nodes.map(node => async () => {
  try {
    const result = await agent(prompt(node), {
      phase: 'Execute',
      label: `${node.id} · ${node.model}/${node.effort}`,
      model: node.model,
      effort: node.effort,
      schema: reportSchema,
      ...(node.kind === 'review' ? { agentType: 'graph-flow:gf-reviewer' } : { isolation: 'worktree' }),
    })
    if (!result || typeof result.reported !== 'boolean' || typeof result.summary !== 'string') {
      return { id: node.id, reported: false, summary: 'No valid reporting acknowledgement returned by the agent' }
    }
    return { id: node.id, reported: result.reported, summary: result.summary }
  } catch (error) {
    return { id: node.id, reported: false, summary: `Agent failed: ${(error && error.message) || String(error)}` }
  }
}))
// reported is the child's acknowledgement, not an independently verified submission or gate verdict.
return args.nodes.map((node, index) => results[index] || {
  id: node.id, reported: false, summary: 'Workflow returned no completion for this node',
})
