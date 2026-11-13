export const meta = {
  name: 'auto-flow',
  description: 'Plan, execute, and verify with models matched to the task tier; escalate once on failure',
  whenToUse: 'Called by the auto-flow skill after the leader session has classified the task',
  phases: [
    { title: 'Triage', detail: 'only when args.tier is missing', model: 'sonnet' },
    { title: 'Explore', detail: 'large only', model: 'sonnet' },
    { title: 'Plan', detail: 'large only', model: 'fable' },
    { title: 'Execute', detail: 'model per tier' },
    { title: 'Verify', detail: 'integration + one full verification' },
    { title: 'Fix', detail: 'once on failure, escalated by rule' },
    { title: 'Re-verify', detail: 'findings only, after Fix' },
  ],
}

// 의존: Claude Code Workflow + Plugin agents/flow-planner.md, agents/flow-verifier.md
// Plugin 이름(auto-flow:*) → bare 이름 → 기본 에이전트 순으로 대체. 내장 Explore는 네임스페이스 없음.
// args: { task, tier?, units?, context?, validator?, worktree?, runId? }

const MODELS = ['haiku', 'sonnet', 'opus', 'fable']
const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']
const EXEC = {
  bulk: { model: 'haiku', effort: 'medium' },
  scoped: { model: 'sonnet', effort: 'medium' },
  daily: { model: 'opus', effort: 'medium' },
}
const VERIFY = {
  bulk: { model: 'sonnet', effort: 'medium' },
  scoped: { model: 'opus', effort: 'medium' },
  daily: { model: 'opus', effort: 'high' },
  large: { model: 'opus', effort: 'high' },
}
const MAX_UNITS = { bulk: 6, scoped: 2, daily: 3, large: 4 }
const HARD_CAP = 9

// 하위 세션에 주는 지시, meta, log, notes는 모두 영어로 쓴다. 사용자에게는 리더가 사용자의 언어로 옮겨 보고한다.
const LEADER = `You are a sub-session of an auto-flow run. The session that started this run is the leader: it owns the user conversation, the plan, and the final report.
- Work and reply in English, whatever language the task text or the repository uses. Keep quoted code, paths, and user-facing strings in their original language.
- Report only to the leader through your result. Do not ask the user questions; state a blocker or an open decision in your result instead.
- Do not start sub-sessions of your own.

`

const TIER_RULES = `Classify the task as one of the tiers below. If you hesitate between two tiers, choose the higher one.
- direct: one file, a few lines, and the location is already known.
- bulk: the same rule applied to many items (classification, extraction, tagging, mechanical replacement). Items are independent and can be checked by format or by sampling.
- scoped: what to change and where is clearly specified. About 5 files or fewer, no design decisions, and a test or build can confirm the result.
- daily: the cause or approach must be found (debugging, a feature across several modules, one or two design choices). Use this when nothing else fits.
- large: changes module boundaries or public interfaces. Refactoring, migration, or architecture change, about 15 files or more, or work that must be split into units and run in parallel.
Raise the tier by one when: there is no automated check / the requirement is ambiguous / the change is hard to undo (data migration, public API, security, concurrency) / the spec is clear but the problem is inherently hard.
units: split only independent work that touches different sets of files. If two units would edit the same file, merge them. When unsure, return one unit.`

const EXEC_SCHEMA = {
  type: 'object',
  properties: {
    status: { enum: ['done', 'partial', 'failed'] },
    summary: { type: 'string' },
    changedFiles: { type: 'array', items: { type: 'string' } },
    checksRun: { type: 'array', items: { type: 'string' } },
    evidence: { type: 'string' },
    lowConfidence: { type: 'array', items: { type: 'string' } },
    branch: { type: 'string' },
  },
  required: ['status', 'summary', 'changedFiles', 'checksRun', 'evidence', 'lowConfidence'],
}
const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    overall: { enum: ['pass', 'fail'] },
    units: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { enum: ['pass', 'fail'] },
          kind: { enum: ['none', 'defect', 'incomplete', 'approach'] },
          findings: { type: 'array', items: { type: 'string' } },
        },
        required: ['id', 'verdict', 'kind', 'findings'],
      },
    },
    checksRun: { type: 'array', items: { type: 'string' } },
    integration: { type: 'string' },
    summary: { type: 'string' },
  },
  required: ['overall', 'units', 'checksRun', 'integration', 'summary'],
}
const TRIAGE_SCHEMA = {
  type: 'object',
  properties: {
    tier: { enum: ['direct', 'bulk', 'scoped', 'daily', 'large'] },
    units: { type: 'array', items: { type: 'string' } },
    reason: { type: 'string' },
  },
  required: ['tier', 'units', 'reason'],
}
const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    indivisible: { type: 'boolean' },
    contracts: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
    units: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          goal: { type: 'string' },
          files: { type: 'array', items: { type: 'string' } },
          acceptance: { type: 'string' },
          checks: { type: 'string' },
          tier: { enum: ['scoped', 'daily'] },
        },
        required: ['id', 'goal', 'files', 'acceptance', 'checks', 'tier'],
      },
    },
  },
  required: ['indivisible', 'contracts', 'risks', 'units'],
}

let spawned = 0
const notes = []
async function run(prompt, opts) {
  if (spawned >= HARD_CAP) throw new Error(`agent cap ${HARD_CAP} reached`)
  spawned++ // 상한은 run() 호출 수이며 에이전트 이름 재시도는 세지 않는다.
  // 하위 세션 이름에 모델·effort를 붙여 T3/workflows 화면에서 바로 보이게 한다
  if (opts.model) opts = { ...opts, label: `${opts.label} · ${opts.model}/${opts.effort || 'default'}` }
  prompt = LEADER + prompt
  if (!opts.agentType) return agent(prompt, opts)
  const { agentType, ...rest } = opts
  const types = ['flow-planner', 'flow-verifier'].includes(agentType)
    ? [`auto-flow:${agentType}`, agentType]
    : [agentType]
  // 대체는 agent()가 throw한 경우(에이전트 이름을 찾지 못함)에만 한다.
  // null은 사용자가 건너뛰었거나 API 오류로 끝난 것이므로 다시 띄우지 않고 그대로 돌려준다.
  for (let i = 0; i < types.length; i++) {
    try { return await agent(prompt, { ...rest, agentType: types[i] }) } catch (e) { /* 다음 이름으로 */ }
    const next = types[i + 1] || 'default'
    notes.push(`agent ${types[i]} unavailable; fell back to the ${next} agent`)
    log(notes[notes.length - 1])
  }
  return agent(prompt, rest)
}

const task = args && args.task
if (!task) throw new Error('args.task is required')
const runId = String(args.runId || 'run').replace(/[^A-Za-z0-9_-]/g, '')
const ctx = args.context ? `\n\n## Context from the leader session\n${args.context}` : ''

// 0. Triage — 메인이 tier를 넘기면 건너뜀
let tier = args.tier
let unitTexts = Array.isArray(args.units) ? args.units : null
if (!tier) {
  phase('Triage')
  const t = await run(`${TIER_RULES}\n\n## Task\n${task}${ctx}\n\nSkim the code briefly if you need to. Do not read deeply.`,
    { phase: 'Triage', label: 'triage', model: 'sonnet', effort: 'low', schema: TRIAGE_SCHEMA })
  if (!t) return { tier: null, outcome: 'unknown', spawned, notes: [...notes, 'no Triage result (skipped or error): nothing was executed'] }
  tier = t.tier
  if (!unitTexts) unitTexts = t.units
  log(`tier: ${tier} — ${t.reason}`)
}
if (tier === 'direct') return { tier, spawned, notes, message: 'direct: the leader session handles it itself' }
if (!EXEC[tier] && tier !== 'large') throw new Error(`unknown tier: ${tier}`)

const reserved = 3 // Verify + Fix + Re-verify
const useWorktree = args.worktree === true

// 1~2. large: Explore → Plan
let units = []
let contracts = ''
if (tier === 'large') {
  phase('Explore')
  const map = await run(`Build a code map for the task below. Summarize concisely: relevant files, module boundaries, public interfaces, call relationships, test locations, and build/test commands. Do not modify code.\n\n## Task\n${task}${ctx}`,
    { phase: 'Explore', label: 'explore', agentType: 'Explore', model: 'sonnet', effort: 'low' })
  phase('Plan')
  const cap = Math.min(MAX_UNITS.large, HARD_CAP - spawned - 1 - reserved)
  const plan = await run(`Plan the task as at most ${cap} independent units.\n\n## Task\n${task}${ctx}\n\n## Code map\n${map || '(no exploration result: read the code yourself and plan)'}`,
    { phase: 'Plan', label: 'plan', agentType: 'flow-planner', model: 'fable', effort: 'high', schema: PLAN_SCHEMA })
  if (!plan) return { tier, outcome: 'unknown', spawned, notes: [...notes, 'no Plan result (skipped or error): nothing was executed'] }
  contracts = plan.contracts
  if (plan.risks.length) log(`plan risks: ${plan.risks.join(' / ')}`)
  if (plan.indivisible || plan.units.length <= 1) {
    const u = plan.units[0] || { id: 'u1', goal: task, files: [], acceptance: '', checks: '' }
    units = [{ ...u, exec: { model: 'fable', effort: 'high' } }]
  } else {
    if (plan.units.length > cap) notes.push(`ran only ${cap} of ${plan.units.length} planned units; call again for the rest: ${plan.units.slice(cap).map(u => u.id).join(', ')}`)
    units = plan.units.slice(0, cap).map(u => ({ ...u, exec: EXEC[u.tier] }))
  }
} else {
  const list = unitTexts && unitTexts.length ? unitTexts : [task]
  const cap = Math.min(MAX_UNITS[tier], HARD_CAP - spawned - reserved)
  if (list.length > cap) notes.push(`ran only ${cap} of ${list.length} units; call again for the rest: ${list.slice(cap).join(' | ')}`)
  units = list.slice(0, cap).map((g, i) => ({ id: `u${i + 1}`, goal: g, files: [], acceptance: '', checks: '', exec: EXEC[tier] }))
}
notes.forEach(n => log(n))

// 3. Execute
phase('Execute')
const parallelOk = useWorktree && units.length > 1
const execPrompt = (u) => `## Whole task\n${task}${ctx}
## Your unit (${u.id})\n${u.goal}
${u.files.length ? `Files you own (do not edit anything else): ${u.files.join(', ')}` : ''}
${contracts ? `## Contracts between units\n${contracts}` : ''}
${u.acceptance ? `## Acceptance criteria\n${u.acceptance}` : ''}
${u.checks ? `## Check commands\n${u.checks}` : ''}
## Rules
- Run only the targeted tests or checks yourself and record the results in checksRun and evidence. Do not run the full build; the integration step runs it once.
- List anything you are unsure about in lowConfidence.
${parallelOk
    ? `- You are in an isolated git worktree. When done, run \`git switch -c auto-flow/${runId}-${u.id}\`, commit your changes, and return that name in branch.`
    : '- Edit the current working tree directly. Do not commit.'}`

const execOne = (u) => run(execPrompt(u), {
  phase: 'Execute', label: `exec:${u.id}`, ...u.exec, schema: EXEC_SCHEMA,
  ...(parallelOk ? { isolation: 'worktree' } : {}),
}).then(r => ({ ...u, result: r }))

let done = []
if (parallelOk) {
  done = await parallel(units.map(u => () => execOne(u)))
  done = done.map((d, i) => d || { ...units[i], result: null })
} else {
  for (const u of units) {
    try { done.push(await execOne(u)) } catch (e) { done.push({ ...u, result: null }) }
  }
}

// 4. Verify — 통합 + 전체 검증 1회
const vcfg = tier === 'bulk' && args.validator ? { model: 'sonnet', effort: 'low' } : VERIFY[tier]
const unitReport = done.map(d => `### ${d.id} (${d.exec.model}/${d.exec.effort})\nGoal: ${d.goal}\n${d.acceptance ? `Acceptance criteria: ${d.acceptance}\n` : ''}Result: ${d.result ? JSON.stringify(d.result) : 'execution failed (no result)'}`).join('\n\n')
const branches = done.map(d => d.result && d.result.branch).filter(Boolean)
const integrate = branches.length
  ? `## Integration\nApply the changes from the branches below to the current working tree, in order: ${branches.join(', ')}
For each branch: \`git diff HEAD...<branch> | git apply --3way\`. On a non-trivial conflict, judge that unit fail(approach) and do not apply its patch.
After applying, find the worktrees in \`git worktree list\` that use an auto-flow/${runId}- branch, remove them with \`git worktree remove --force\`, and delete those branches with \`git branch -D\`. Do not touch any other branch or worktree.`
  : '## Integration\nThe changes are already in the current working tree.'

const verifyPrompt = (focus) => `## Task\n${task}${ctx}\n\n${integrate}\n\n## Unit results\n${unitReport}
## Verification
${tier === 'bulk' && args.validator
    ? `Run the validator command: ${args.validator}\nInspect by hand only a sample of the failed items and the lowConfidence items.`
    : tier === 'bulk'
      ? 'Inspect by hand a sample of 10% of the results, at most 30 items, and every lowConfidence item.'
      : 'Run the full build and tests once, then try to refute that each unit actually met its goal and acceptance criteria.'}
${focus || ''}`

phase('Verify')
let verify = await run(verifyPrompt(''), { phase: 'Verify', label: 'verify', agentType: 'flow-verifier', ...vcfg, schema: VERIFY_SCHEMA })

// 5. Fix — 실패 시 1회, 규칙대로 상향
function escalate(exec, kind) {
  if (tier === 'bulk') return { model: 'sonnet', effort: 'medium' }
  if (kind === 'approach') {
    const i = MODELS.indexOf(exec.model)
    if (exec.model === 'fable') return null
    return { model: MODELS[i + 1], effort: 'medium' }
  }
  const e = EFFORTS.indexOf(exec.effort)
  return { model: exec.model, effort: EFFORTS[Math.min(e + 1, exec.model === 'opus' ? 2 : 4)] }
}

let fix = null, reverify = null, unresolved = []
const failed = (verify && verify.units || []).filter(u => u.verdict === 'fail')
if (verify && verify.overall === 'fail' && failed.length) {
  const plans = failed.map(f => {
    const unit = done.find(d => d.id === f.id) || done[0]
    return { f, cfg: escalate(unit.exec, f.kind) }
  })
  unresolved = plans.filter(p => !p.cfg).map(p => p.f)
  const fixable = plans.filter(p => p.cfg)
  if (fixable.length && spawned + 2 <= HARD_CAP) {
    const cfg = fixable.reduce((a, p) => {
      const ma = MODELS.indexOf(a.model), mb = MODELS.indexOf(p.cfg.model)
      if (mb > ma) return p.cfg
      if (mb === ma && EFFORTS.indexOf(p.cfg.effort) > EFFORTS.indexOf(a.effort)) return p.cfg
      return a
    }, fixable[0].cfg)
    log(`fix: ${fixable.map(p => `${p.f.id}(${p.f.kind})`).join(', ')} → ${cfg.model}/${cfg.effort}`)
    phase('Fix')
    fix = await run(`## Task\n${task}${ctx}\n\n## Units that failed verification, with findings\n${fixable.map(p => `### ${p.f.id} [${p.f.kind}]\n${p.f.findings.join('\n')}`).join('\n\n')}
${contracts ? `## Contracts between units\n${contracts}` : ''}
Fix the current working tree directly. Do not commit. Resolve every finding, run the related tests, and record them in checksRun and evidence.`,
      { phase: 'Fix', label: 'fix', ...cfg, schema: EXEC_SCHEMA })
    phase('Re-verify')
    reverify = await run(`## Task\n${task}${ctx}\n\nThe changes are already in the current working tree. Do not integrate anything.
## Findings from the previous verification\n${fixable.map(p => `### ${p.f.id} [${p.f.kind}]\n${p.f.findings.join('\n')}`).join('\n\n')}
## Fix result\n${JSON.stringify(fix)}
Check only that the findings are resolved and that nothing regressed. Run the full tests once.`,
      { phase: 'Re-verify', label: 'reverify', agentType: 'flow-verifier', ...vcfg, schema: VERIFY_SCHEMA })
  } else if (fixable.length) {
    notes.push('Fix was not run because of the agent cap')
  }
  if (unresolved.length) notes.push(`units whose approach failed even at fable/high are reported without escalation: ${unresolved.map(u => u.id).join(', ')}`)
}

const final = reverify || verify
return {
  tier,
  outcome: final ? final.overall : 'unknown',
  units: done.map(d => ({ id: d.id, model: `${d.exec.model}/${d.exec.effort}`, goal: d.goal, status: d.result ? d.result.status : 'no-result', changedFiles: d.result ? d.result.changedFiles : [] })),
  verify,
  fix,
  reverify,
  unresolved,
  spawned,
  notes,
}
