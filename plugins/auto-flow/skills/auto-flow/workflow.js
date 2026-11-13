export const meta = {
  name: 'auto-flow',
  description: '작업 tier에 맞는 모델로 계획·실행·통합 검증하고 실패 시 1회 상향 수정',
  whenToUse: 'auto-flow 스킬이 메인 세션에서 분류를 마친 뒤 호출한다',
  phases: [
    { title: 'Triage', detail: 'args.tier가 없을 때만', model: 'sonnet' },
    { title: 'Explore', detail: 'large만', model: 'sonnet' },
    { title: 'Plan', detail: 'large만', model: 'fable' },
    { title: 'Execute', detail: 'tier별 모델' },
    { title: 'Verify', detail: '통합 + 전체 검증 1회' },
    { title: 'Fix', detail: '실패 시 1회, 규칙대로 상향' },
    { title: 'Re-verify', detail: 'Fix 뒤 지적 항목만' },
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

const TIER_RULES = `작업을 아래 중 하나로 분류하라. 두 tier 사이에서 망설여지면 높은 쪽을 고른다.
- direct: 파일 1개, 수 줄 수준이고 위치를 이미 안다.
- bulk: 같은 규칙을 많은 항목에 반복 적용한다(분류·추출·태깅·기계적 치환). 항목끼리 독립이고 형식이나 표본으로 검사할 수 있다.
- scoped: 무엇을 어디서 바꿀지 명세가 분명하다. 파일 약 5개 이하, 설계 결정이 없고, 테스트나 빌드로 통과 여부를 확인할 수 있다.
- daily: 원인이나 접근을 스스로 찾아야 한다(디버깅, 여러 모듈에 걸친 기능, 설계 선택 1~2개). 어디에도 맞지 않으면 여기다.
- large: 모듈 경계나 공개 인터페이스를 바꾼다. 리팩터링·마이그레이션·아키텍처 변경, 파일 약 15개 이상, 또는 여러 단위로 나눠 병렬로 해야 한다.
상향 조건(한 단계 올림): 자동 검증 수단이 없다 / 요구가 모호하다 / 되돌리기 어렵다(데이터 마이그레이션, 공개 API, 보안, 동시성) / 명세는 분명하지만 본질적으로 어렵다.
units: 서로 다른 파일 집합을 건드리는 독립 작업만 나눈다. 같은 파일을 두 단위가 고치면 하나로 합친다. 확신이 없으면 1개.`

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
  if (spawned >= HARD_CAP) throw new Error(`에이전트 상한 ${HARD_CAP} 도달`)
  spawned++ // 상한은 run() 호출 수이며 에이전트 이름 재시도는 세지 않는다.
  if (!opts.agentType) return agent(prompt, opts)
  const { agentType, ...rest } = opts
  const types = ['flow-planner', 'flow-verifier'].includes(agentType)
    ? [`auto-flow:${agentType}`, agentType]
    : [agentType]
  for (let i = 0; i < types.length; i++) {
    let r = null
    try { r = await agent(prompt, { ...rest, agentType: types[i] }) } catch (e) { r = null }
    if (r !== null) return r
    const next = types[i + 1] || '기본'
    notes.push(`${types[i]} 에이전트를 쓰지 못해 ${next} 에이전트로 대체`)
    log(notes[notes.length - 1])
  }
  return agent(prompt, rest)
}

const task = args && args.task
if (!task) throw new Error('args.task가 필요하다')
const runId = (args.runId || 'run').replace(/[^A-Za-z0-9_-]/g, '')
const ctx = args.context ? `\n\n## 메인 세션이 넘긴 맥락\n${args.context}` : ''

// 0. Triage — 메인이 tier를 넘기면 건너뜀
let tier = args.tier
let unitTexts = Array.isArray(args.units) ? args.units : null
if (!tier) {
  phase('Triage')
  const t = await run(`${TIER_RULES}\n\n## 작업\n${task}${ctx}\n\n필요하면 코드를 짧게 훑어 판단하라. 깊게 읽지 마라.`,
    { phase: 'Triage', label: 'triage', model: 'sonnet', effort: 'low', schema: TRIAGE_SCHEMA })
  tier = t.tier
  if (!unitTexts) unitTexts = t.units
  log(`분류: ${tier} — ${t.reason}`)
}
if (tier === 'direct') return { tier, spawned, notes, message: 'direct: 메인 세션이 직접 처리한다' }
if (!EXEC[tier] && tier !== 'large') throw new Error(`알 수 없는 tier: ${tier}`)

const reserved = 3 // Verify + Fix + Re-verify
const useWorktree = args.worktree === true

// 1~2. large: Explore → Plan
let units = []
let contracts = ''
if (tier === 'large') {
  phase('Explore')
  const map = await run(`다음 작업에 관련된 코드 지도를 만들어라. 관련 파일·모듈 경계·공개 인터페이스·호출 관계·테스트 위치·빌드/테스트 명령을 간결히 정리하라. 코드는 수정하지 마라.\n\n## 작업\n${task}${ctx}`,
    { phase: 'Explore', label: 'explore', agentType: 'Explore', model: 'sonnet', effort: 'low' })
  phase('Plan')
  const cap = Math.min(MAX_UNITS.large, HARD_CAP - spawned - 1 - reserved)
  const plan = await run(`작업을 최대 ${cap}개의 독립 단위로 계획하라.\n\n## 작업\n${task}${ctx}\n\n## 코드 지도\n${map}`,
    { phase: 'Plan', label: 'plan', agentType: 'flow-planner', model: 'fable', effort: 'high', schema: PLAN_SCHEMA })
  contracts = plan.contracts
  if (plan.risks.length) log(`계획 위험: ${plan.risks.join(' / ')}`)
  if (plan.indivisible || plan.units.length <= 1) {
    const u = plan.units[0] || { id: 'u1', goal: task, files: [], acceptance: '', checks: '' }
    units = [{ ...u, exec: { model: 'fable', effort: 'high' } }]
  } else {
    if (plan.units.length > cap) notes.push(`계획 단위 ${plan.units.length}개 중 ${cap}개만 실행, 나머지는 다시 호출 필요: ${plan.units.slice(cap).map(u => u.id).join(', ')}`)
    units = plan.units.slice(0, cap).map(u => ({ ...u, exec: EXEC[u.tier] }))
  }
} else {
  const list = unitTexts && unitTexts.length ? unitTexts : [task]
  const cap = Math.min(MAX_UNITS[tier], HARD_CAP - spawned - reserved)
  if (list.length > cap) notes.push(`단위 ${list.length}개 중 ${cap}개만 실행, 나머지는 다시 호출 필요: ${list.slice(cap).join(' | ')}`)
  units = list.slice(0, cap).map((g, i) => ({ id: `u${i + 1}`, goal: g, files: [], acceptance: '', checks: '', exec: EXEC[tier] }))
}
notes.forEach(n => log(n))

// 3. Execute
phase('Execute')
const parallelOk = useWorktree && units.length > 1
const execPrompt = (u) => `## 전체 작업\n${task}${ctx}
## 네 단위 (${u.id})\n${u.goal}
${u.files.length ? `소유 파일(이 밖은 고치지 마라): ${u.files.join(', ')}` : ''}
${contracts ? `## 단위 사이 계약\n${contracts}` : ''}
${u.acceptance ? `## 수용 기준\n${u.acceptance}` : ''}
${u.checks ? `## 검증 명령\n${u.checks}` : ''}
## 규칙
- 대상 테스트나 검사만 직접 돌리고 checksRun과 evidence에 결과를 남겨라. 전체 빌드는 통합 단계에서 1회 하므로 하지 마라.
- 확신이 낮은 부분은 lowConfidence에 적어라.
${parallelOk
    ? `- 너는 격리된 git worktree에 있다. 끝나면 \`git switch -c auto-flow/${runId}-${u.id}\` 후 변경을 커밋하고 branch에 그 이름을 반환하라.`
    : '- 현재 작업 트리를 직접 수정하라. 커밋하지 마라.'}`

const execOne = (u) => run(execPrompt(u), {
  phase: 'Execute', label: `exec:${u.id}:${u.exec.model}`, ...u.exec, schema: EXEC_SCHEMA,
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
const unitReport = done.map(d => `### ${d.id} (${d.exec.model}/${d.exec.effort})\n목표: ${d.goal}\n${d.acceptance ? `수용 기준: ${d.acceptance}\n` : ''}결과: ${d.result ? JSON.stringify(d.result) : '실행 실패(결과 없음)'}`).join('\n\n')
const branches = done.map(d => d.result && d.result.branch).filter(Boolean)
const integrate = branches.length
  ? `## 통합\n아래 브랜치의 변경을 현재 작업 트리에 순서대로 적용하라: ${branches.join(', ')}
각 브랜치마다 \`git diff HEAD...<branch> | git apply --3way\`. 사소하지 않은 충돌이 나면 해당 단위를 fail(approach)로 판정하고 그 패치는 적용하지 마라.
적용 후 \`git worktree list\`에서 auto-flow/${runId}- 브랜치를 쓰는 worktree를 \`git worktree remove --force\`로 지우고 그 브랜치를 \`git branch -D\`로 지워라. 다른 브랜치·worktree는 건드리지 마라.`
  : '## 통합\n변경은 이미 현재 작업 트리에 있다.'

const verifyPrompt = (focus) => `## 작업\n${task}${ctx}\n\n${integrate}\n\n## 단위 결과\n${unitReport}
## 검증
${tier === 'bulk' && args.validator
    ? `검증 명령을 실행하라: ${args.validator}\n실패 항목과 lowConfidence 항목만 표본으로 직접 확인하라.`
    : tier === 'bulk'
      ? '결과의 10% 또는 최대 30개를 표본으로 직접 확인하고, lowConfidence 항목은 전부 확인하라.'
      : '전체 빌드·테스트를 1회 돌리고, 각 단위가 목표와 수용 기준을 실제로 달성했는지 반박을 시도하라.'}
${focus || ''}`

phase('Verify')
let verify = await run(verifyPrompt(''), { phase: 'Verify', label: `verify:${vcfg.model}`, agentType: 'flow-verifier', ...vcfg, schema: VERIFY_SCHEMA })

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
    log(`수정: ${fixable.map(p => `${p.f.id}(${p.f.kind})`).join(', ')} → ${cfg.model}/${cfg.effort}`)
    phase('Fix')
    fix = await run(`## 작업\n${task}${ctx}\n\n## 검증에서 실패한 단위와 지적\n${fixable.map(p => `### ${p.f.id} [${p.f.kind}]\n${p.f.findings.join('\n')}`).join('\n\n')}
${contracts ? `## 단위 사이 계약\n${contracts}` : ''}
현재 작업 트리를 직접 고쳐라. 커밋하지 마라. 지적된 항목을 모두 해결하고 관련 테스트를 돌려 checksRun과 evidence에 남겨라.`,
      { phase: 'Fix', label: `fix:${cfg.model}`, ...cfg, schema: EXEC_SCHEMA })
    phase('Re-verify')
    reverify = await run(`## 작업\n${task}${ctx}\n\n변경은 이미 현재 작업 트리에 있다. 통합은 하지 마라.
## 이전 검증의 지적\n${fixable.map(p => `### ${p.f.id} [${p.f.kind}]\n${p.f.findings.join('\n')}`).join('\n\n')}
## 수정 결과\n${JSON.stringify(fix)}
지적 항목이 해결됐는지와 회귀가 없는지만 확인하라. 전체 테스트는 1회 돌려라.`,
      { phase: 'Re-verify', label: `reverify:${vcfg.model}`, agentType: 'flow-verifier', ...vcfg, schema: VERIFY_SCHEMA })
  } else if (fixable.length) {
    notes.push('에이전트 상한 때문에 Fix를 실행하지 못함')
  }
  if (unresolved.length) notes.push(`fable/high에서도 접근이 틀린 단위는 자동 상향 없이 보고: ${unresolved.map(u => u.id).join(', ')}`)
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
