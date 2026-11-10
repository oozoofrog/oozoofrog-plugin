import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type {
  Activity, ActivityEvent, AiState, Board, BoardCheck, BoardDecision, BoardTask, CheckResult, ServerState, View,
} from './types'

// Read-only view of guided-execution records (.agent-loop/<run>/plan.json + state.json).
// loop_control.py stays the only writer; nothing here edits loop files.

const PANE = 'guided-board'
const POLL_MS = 2000
const SUMMARY_GAP_MS = 20000
const RUN_ID = /^[a-z0-9][a-z0-9_-]{0,63}$/

const board = atom({ plugin: 'guided-execution', key: 'board' } as const, null as Board | null, { shape: 'board-1' })
const view = atom({ plugin: 'guided-execution', key: 'view' } as const, 'list' as View, { shape: 'view-1' })
const server = atom({ plugin: 'guided-execution', key: 'server' } as const, { phase: 'off' } as ServerState, {
  shape: 'server-1',
})
const ai = atom({ plugin: 'guided-execution', key: 'ai' } as const, { isEnabled: true, phase: 'idle' } as AiState, {
  shape: 'ai-1',
})
const pinnedRun = atom({ plugin: 'guided-execution', key: 'pinnedRun' } as const, '', { shape: 'pinned-1' })
const autoOpenedRun = atom({ plugin: 'guided-execution', key: 'autoOpenedRun' } as const, '', { shape: 'opened-1' })
const activity = atom({ plugin: 'guided-execution', key: 'activity' } as const,
  { events: [], counts: {}, now: 0 } as Activity, { shape: 'activity-1' })

/** Tool calls that belong to no running task land on this node. */
export const SESSION = '__session'
const MAX_EVENTS = 120
const PANE_EVENTS = 40

const GLYPH: Record<string, string> = {
  passed: '✓', running: '▶', failed: '✗', blocked: '⏸', stale: '↺', cancelled: '⊘', pending: '○',
}
const LABEL: Record<string, string> = {
  pending: '대기', running: '진행', passed: '통과', failed: '실패', blocked: '차단', stale: '재검증',
  cancelled: '취소', approved: '승인', rejected: '반려', answered: '답변', revision_requested: '수정 요청',
  mixed: '상충', not_run: '미실행', unrecorded: '미기록',
}
const COLOR: Record<string, string> = {
  passed: 'success', approved: 'success', answered: 'success', failed: 'error', rejected: 'error', mixed: 'error',
  blocked: 'warning', stale: 'warning', revision_requested: 'warning', running: 'suggestion',
}
const label = (s: string) => LABEL[s] ?? s
const tone = (s: string) => COLOR[s] ?? 'inactive'
const clip = (s: unknown, n: number) => {
  const text = typeof s === 'string' ? s.replace(/\s+/g, ' ').trim() : ''
  return text.length > n ? text.slice(0, n - 1) + '…' : text
}

type Json = Record<string, unknown>
const obj = (v: unknown): Json => (v && typeof v === 'object' && !Array.isArray(v) ? (v as Json) : {})
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const strs = (v: unknown): string[] => arr(v).filter((x): x is string => typeof x === 'string')

const satisfied = (d: BoardDecision | undefined) =>
  !!d && d.status === 'resolved' && (d.outcome === 'answered' || d.outcome === 'approved')

/** Mirrors loop_workspace.status(): ready = pending/failed/stale with deps passed, gates open, attempts left. */
export function toBoard(runId: string, workspace: string, planText: string, stateText: string, readAt: number): Board {
  const plan = obj(JSON.parse(planText))
  const state = obj(JSON.parse(stateText))
  const taskStates = obj(state.tasks)
  const decisionStates = obj(state.decisions)
  const planTasks = arr(plan.tasks).map(obj)
  const ids = planTasks.map(t => String(t.id))
  if (ids.length !== Object.keys(taskStates).length || ids.some(id => !(id in taskStates))) {
    throw new Error('plan.json과 state.json의 작업 목록이 다릅니다')
  }
  const retried = new Set<string>()
  const startedAt = new Map<string, number>()
  const lastRecord = new Map<string, string>()
  for (const event of arr(state.history).map(obj)) {
    const at = Date.parse(String(event.timestamp ?? ''))
    for (const [name, prev] of Object.entries(obj(event.previous_tasks))) {
      if (event.action === 'start' && obj(prev).status === 'failed') retried.add(name)
      if (event.action === 'start' && name === event.task && !Number.isNaN(at)) startedAt.set(name, at)
      lastRecord.set(name, recordLabel(event, name))
    }
  }
  const decisions: BoardDecision[] = arr(plan.decisions).map(obj).map(d => {
    const s = obj(decisionStates[String(d.id)])
    return {
      id: String(d.id), kind: String(d.kind ?? ''), question: String(d.question ?? ''),
      status: String(s.status ?? 'pending'), ...(typeof s.outcome === 'string' ? { outcome: s.outcome } : {}),
    }
  })
  const tasks: BoardTask[] = planTasks.map(t => {
    const s = obj(taskStates[String(t.id)])
    const status = String(s.status ?? 'pending')
    const evidence = arr(s.evidence).map(obj)
    const checks: BoardCheck[] = arr(t.checks).map(obj).map(c => {
      const results = evidence.filter(r => r.check_id === c.id).map(r => String(r.result))
      const result: CheckResult = status === 'stale' ? 'stale' : results.length > 1 ? 'mixed'
        : results.length === 1 ? (results[0] as CheckResult) : 'unrecorded'
      return { id: String(c.id), result }
    })
    return {
      id: String(t.id), title: String(t.title ?? t.id), status,
      attempts: Number(s.attempts ?? 0), maxAttempts: Number(t.max_attempts ?? 3),
      dependsOn: strs(t.depends_on), decisionIds: strs(t.decision_ids),
      ...(typeof s.block_reason === 'string' && s.block_reason ? { blockReason: s.block_reason } : {}),
      checks, isRetried: retried.has(String(t.id)),
      reads: strs(t.reads), writes: strs(t.writes),
      ...(status === 'running' && startedAt.has(String(t.id)) ? { startedAt: startedAt.get(String(t.id)) } : {}),
      ...(lastRecord.has(String(t.id)) ? { lastRecord: lastRecord.get(String(t.id)) } : {}),
    }
  })
  const byId = new Map(tasks.map(t => [t.id, t]))
  const byDecision = new Map(decisions.map(d => [d.id, d]))
  const ready = tasks.filter(t =>
    ['pending', 'failed', 'stale'].includes(t.status) && t.attempts < t.maxAttempts &&
    t.dependsOn.every(d => byId.get(d)?.status === 'passed') &&
    t.decisionIds.every(d => satisfied(byDecision.get(d)))).map(t => t.id)
  return {
    runId, workspace, goal: String(plan.goal ?? ''), tasks, decisions, ready,
    isComplete: tasks.length > 0 && tasks.every(t => t.status === 'passed'), readAt, otherRuns: [],
  }
}

const ACTION: Record<string, string> = {
  start: '시작', 'set-revision': '리비전 갱신', 'record-check': '검증 기록', finish: '종료',
  invalidate: '무효화', block: '차단', cancel: '취소',
}

function recordLabel(event: Json, name: string): string {
  const action = String(event.action ?? '')
  if (event.task !== name) return `${clip(String(event.task ?? ''), 24)}에서 무효화`
  const record = obj(event.record)
  if (action === 'record-check') return `검증 ${clip(String(record.check_id ?? ''), 24)} ${label(String(record.result ?? ''))}`
  return ACTION[action] ?? action
}

const elapsed = (ms: number) => {
  const total = Math.max(0, Math.floor(ms / 1000))
  const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60), sec = total % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return h ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`
}

const inScope = (path: string, scope: string) => scope === '.' || path === scope || path.startsWith(scope + '/')

/** Short, project-relative description of what a tool call works on. */
export function targetOf(tool: string, input: Record<string, unknown>, root: string): string {
  const pick = input.file_path ?? input.notebook_path ?? input.path ?? input.pattern ?? input.url ??
    input.description ?? input.command ?? input.prompt ?? Object.values(input).find(v => typeof v === 'string') ?? ''
  const text = String(pick)
  const relative = root && text.startsWith(root + '/') ? text.slice(root.length + 1) : text
  return clip(tool === 'Bash' && typeof input.description === 'string' ? input.description : relative, 120)
}

/**
 * Which task a tool call belongs to. An explicit `loop_control.py … --task id`, then a subagent
 * already tied to a task, then the only running task, then a file inside exactly one running
 * task's write (then read) scope; everything else is session activity.
 */
export function attribute(
  tool: string, input: Record<string, unknown>, b: Board | null, root: string,
  agentTasks: ReadonlyMap<string, string>, agentId?: string,
): { task: string; via: string } {
  if (!b) return { task: SESSION, via: 'none' }
  const ids = new Set(b.tasks.map(t => t.id))
  const command = typeof input.command === 'string' ? input.command : ''
  const named = /loop_control\.py\b[^\n]*--task[ =]([a-z0-9][a-z0-9_-]{0,63})/.exec(command)?.[1]
  if (named && ids.has(named) && (!command.includes('.agent-loop/') || command.includes(`.agent-loop/${b.runId}`))) {
    return { task: named, via: 'command' }
  }
  if (agentId && agentTasks.has(agentId) && ids.has(agentTasks.get(agentId)!)) {
    return { task: agentTasks.get(agentId)!, via: 'agent' }
  }
  const running = b.tasks.filter(t => t.status === 'running')
  if (running.length === 1) return { task: running[0]!.id, via: 'running' }
  if (running.length > 1) {
    const raw = String(input.file_path ?? input.notebook_path ?? input.path ?? '')
    const path = root && raw.startsWith(root + '/') ? raw.slice(root.length + 1) : raw
    if (path) {
      for (const key of ['writes', 'reads'] as const) {
        const hits = running.filter(t => t[key].some(scope => inScope(path, scope)))
        if (hits.length === 1) return { task: hits[0]!.id, via: 'scope' }
      }
    }
  }
  return { task: SESSION, via: running.length ? 'ambiguous' : 'idle' }
}

/** One line for the band: progress, what runs, what waits on the person. */
export function summaryLine(b: Board, events?: readonly ActivityEvent[]): string {
  const passed = b.tasks.filter(t => t.status === 'passed').length
  const running = b.tasks.filter(t => t.status === 'running').map(t => t.title)
  const waiting = b.decisions.filter(d => d.status === 'pending').length
  const blocked = b.tasks.filter(t => t.status === 'blocked').length
  const parts = [`${b.runId}`, `통과 ${passed}/${b.tasks.length}`]
  const now = events?.findLast(e => e.phase === 'running' && e.task !== SESSION)
  if (running.length) parts.push(`진행: ${clip(running.join(', '), 40)}${now ? ` (${now.tool} ${clip(now.target, 24)})` : ''}`)
  else if (b.ready.length) parts.push(`다음: ${clip(b.tasks.find(t => t.id === b.ready[0])?.title, 32)}`)
  if (waiting) parts.push(`결정 대기 ${waiting}`)
  if (blocked) parts.push(`차단 ${blocked}`)
  if (b.error) parts.push('기록 읽기 불일치')
  return parts.join(' · ')
}

/** Relation view rows: prerequisites, decision gates, checks and recorded retries per task. */
export function relationRows(b: Board, act?: Activity): { text: string; color?: string; dim?: boolean }[] {
  const rows: { text: string; color?: string; dim?: boolean }[] = []
  const byDecision = new Map(b.decisions.map(d => [d.id, d]))
  for (const t of b.tasks) {
    const from = t.dependsOn.length ? `${t.dependsOn.join(' + ')} ──▶ ` : ''
    const calls = act?.counts[t.id]?.calls
    const busy = act?.events.findLast(e => e.task === t.id && e.phase === 'running')
    rows.push({ text: `${from}${t.id}  [${label(t.status)}]${calls ? ` · 도구 ${calls}` : ''}${busy ? ` · ◌ ${busy.tool}` : ''}`, color: tone(t.status) })
    for (const d of t.decisionIds) {
      const dec = byDecision.get(d)
      const state = dec?.status === 'resolved' ? label(dec.outcome ?? 'resolved') : '대기'
      rows.push({ text: `   ◆ ${d} ═▶ ${t.id}  (결정 ${state})`, color: satisfied(dec) ? 'success' : 'warning' })
    }
    for (const c of t.checks) {
      rows.push({ text: `   ⬡ ${t.id} ─▶ ${c.id}  ${label(c.result)}`, color: tone(c.result), dim: c.result === 'unrecorded' })
    }
    if (t.isRetried) rows.push({ text: `   ↺ ${t.id} 실패 후 재시작 기록`, color: 'warning' })
  }
  return rows
}

type Row = { text: string; color?: string; dim?: boolean }

const seconds = (ms: number) => (ms < 10000 ? `${(ms / 1000).toFixed(1)}s` : elapsed(ms))

/** A node's live lines: calls in flight, the latest finished calls, then totals and the last record. */
export function liveRows(t: BoardTask | { id: string; status: string; startedAt?: number; lastRecord?: string },
  act: Activity, max = 3): Row[] {
  const mine = act.events.filter(e => e.task === t.id)
  const rows: Row[] = mine.filter(e => e.phase === 'running').slice(-2).reverse().map(e => ({
    text: `◌ ${e.tool} ${e.target} · ${seconds(act.now - e.startedAt)}${e.agent ? ' · 서브에이전트' : ''}`, color: 'suggestion',
  }))
  for (const e of mine.filter(x => x.phase !== 'running').slice(-max).reverse()) {
    rows.push({ text: `${e.phase === 'error' ? '✗' : '●'} ${e.tool} ${e.target} · ${seconds((e.endedAt ?? e.startedAt) - e.startedAt)}`,
      color: e.phase === 'error' ? 'error' : undefined, dim: e.phase !== 'error' })
  }
  const c = act.counts[t.id]
  const facts = [
    t.status === 'running' && t.startedAt ? `경과 ${elapsed(act.now - t.startedAt)}` : '',
    c ? `도구 ${c.calls}${c.errors ? ` · 오류 ${c.errors}` : ''}` : '',
    t.lastRecord ? `기록: ${t.lastRecord}` : '',
  ].filter(Boolean)
  if (facts.length) rows.push({ text: facts.join(' · '), dim: true })
  return rows
}

const SUMMARY_SYSTEM = `너는 소프트웨어 작업 현황을 파이프라인 단계로 묶는 정리 도구다.
입력의 records(실행 기록)와 activity(최근 세션 활동)만 근거로 삼는다.
JSON 객체 하나만 출력한다. 다른 글이나 코드 블록 표시는 쓰지 않는다.
형식: {"headline":"지금 상황 한 문장(60자 이내)","activity":"최근 세션 활동 한 문장(80자 이내)","stages":[{"id":"s1","label":"단계 이름(12자 이내)","kind":"plan|build|verify|decide|deliver|other","refs":["작업 id"],"note":"한 줄(40자 이내)"}],"edges":[{"from":"s1","to":"s2"}]}
규칙: stages는 작업 흐름 순서로 2~6개. records.tasks의 모든 id를 정확히 한 단계의 refs에 넣는다.
통과·실패 같은 상태를 새로 판정하지 않는다. 기록에 없는 일은 note에만 적는다. 한국어로 쓴다.`

function activityDigest(messages: readonly { role: string; text: string; toolUses: readonly { tool: string; input: Record<string, unknown>; isError?: true }[] }[]): string[] {
  const lines: string[] = []
  for (const m of messages.slice(-30)) {
    if (m.text.trim()) lines.push(`${m.role === 'user' ? '사용자' : 'Claude'}: ${clip(m.text, 160)}`)
    for (const use of m.toolUses) {
      const input = use.input
      const target = input.description ?? input.file_path ?? input.path ?? input.pattern ?? input.command ?? input.url ?? ''
      lines.push(`도구 ${use.tool}${use.isError ? ' (오류)' : ''}: ${clip(String(target), 80)}`)
    }
  }
  return lines.slice(-60)
}

export function parseSummary(text: string): Json | undefined {
  const start = text.indexOf('{')
  const end = text.lastIndexOf('}')
  if (start < 0 || end <= start) return undefined
  try {
    const value = JSON.parse(text.slice(start, end + 1))
    return value && typeof value === 'object' && Array.isArray((value as Json).stages) ? (value as Json) : undefined
  } catch {
    return undefined
  }
}

// Module variables restart on every reload; durable values live in atoms.
const agentTasks = new Map<string, string>()
let posting = false
let postAgain = false
let lastKey = ''
let live: { url: string; token: string; port: number; runId: string; stop: () => void } | undefined
let isDirty = true
let isSummarizing = false
let lastSummaryAt = 0

async function refresh($: EngineInterface) {
  const root = await $.session.root()
  const base = `${root}/.agent-loop`
  if (!(await $.fs.exists(base))) {
    if (lastKey !== 'none') {
      lastKey = 'none'
      await update($, board, () => null)
    }
    return
  }
  const runs: { name: string; mtime: number; planMtime: number }[] = []
  for (const entry of await $.fs.list(base)) {
    if (entry.kind !== 'dir' || !RUN_ID.test(entry.name)) continue
    const state = await $.fs.stat(`${base}/${entry.name}/state.json`).catch(() => undefined)
    const plan = await $.fs.stat(`${base}/${entry.name}/plan.json`).catch(() => undefined)
    if (state?.kind === 'file' && plan?.kind === 'file') {
      runs.push({ name: entry.name, mtime: state.mtimeMs, planMtime: plan.mtimeMs })
    }
  }
  if (!runs.length) {
    if (lastKey !== 'none') {
      lastKey = 'none'
      await update($, board, () => null)
    }
    return
  }
  runs.sort((a, b) => b.mtime - a.mtime)
  const pinned = await read($, pinnedRun)
  const chosen = runs.find(r => r.name === pinned) ?? runs[0]!
  const key = `${chosen.name}:${chosen.mtime}:${chosen.planMtime}:${runs.map(r => r.name).join(',')}`
  if (key === lastKey) return
  const workspace = `${base}/${chosen.name}`
  const now = await $.clock.now()
  const others = runs.map(r => r.name).filter(n => n !== chosen.name)
  try {
    const [planText, stateText] = await Promise.all([
      $.fs.read(`${workspace}/plan.json`), $.fs.read(`${workspace}/state.json`),
    ])
    const next = { ...toBoard(chosen.name, workspace, planText, stateText, now), otherRuns: others }
    lastKey = key
    isDirty = true
    await update($, board, () => next)
    const opened = await read($, autoOpenedRun)
    if (!next.isComplete && opened !== chosen.name) {
      await update($, autoOpenedRun, () => chosen.name)
      void $.ui.open({ id: PANE, title: 'Guided 할 일' })
    }
  } catch (error) {
    // A torn read (plan/state written in between) keeps the last good board and retries next tick.
    const reason = clip(error instanceof Error ? error.message : String(error), 120)
    await update($, board, prev =>
      prev && prev.runId === chosen.name ? { ...prev, error: reason, otherRuns: others } : {
        runId: chosen.name, workspace, goal: '', tasks: [], decisions: [], ready: [], isComplete: false,
        readAt: now, otherRuns: others, error: reason,
      })
  }
}

async function openUrl($: EngineInterface, url: string) {
  const isWindows = (await $.env.get('OS').catch(() => undefined)) === 'Windows_NT'
  const commands = isWindows ? [['cmd', '/c', 'start', '', url]] : [['open', url], ['xdg-open', url]]
  for (const argv of commands) {
    const ran = await $.process.run(argv, { timeoutMs: 10000 }).catch(() => undefined)
    if (ran && ran.exitCode === 0) return true
  }
  return false
}

async function startServer($: EngineInterface) {
  const b = await read($, board)
  if (!b || !b.tasks.length) return
  if (live && live.runId === b.runId) {
    await openUrl($, live.url)
    return
  }
  live?.stop()
  live = undefined
  await update($, server, () => ({ phase: 'starting', runId: b.runId }))
  const script = `${$.plugin.root}/skills/guided-execution/scripts/serve_dashboard.py`
  const child = $.process.spawn({ argv: ['python3', script, '--workspace', b.workspace] })
  const runId = b.runId
  void (async () => {
    let buffer = ''
    let stderr = ''
    let announced = false
    try {
      for await (const piece of child) {
        if (piece.stream === 'stderr') {
          stderr = clip(stderr + piece.text, 300)
          continue
        }
        if (announced) continue
        buffer += piece.text
        const newline = buffer.indexOf('\n')
        if (newline < 0) continue
        const info = obj(JSON.parse(buffer.slice(0, newline)))
        announced = true
        const url = String(info.url)
        live = { url, token: String(info.token), port: Number(info.port), runId, stop: () => void child.return(undefined as never).catch(() => undefined) }
        isDirty = true
        await update($, server, () => ({ phase: 'on', url, runId }))
        void flushActivity($)
        // The Link in the pane stays usable when no opener is found.
        await openUrl($, url).catch(() => false)
      }
    } catch (error) {
      stderr = clip(`${stderr} ${error instanceof Error ? error.message : String(error)}`, 300)
    }
    if (live?.runId === runId) live = undefined
    await update($, server, prev =>
      prev.runId !== runId ? prev : announced ? { phase: 'off' } : { phase: 'error', runId, error: stderr || '서버가 시작되지 않았습니다' })
  })()
}

async function stopServer($: EngineInterface) {
  live?.stop()
  live = undefined
  await update($, server, () => ({ phase: 'off' }))
}

async function track($: EngineInterface, change: (events: ActivityEvent[]) => ActivityEvent[], counted?: ActivityEvent) {
  const now = await $.clock.now()
  await update($, activity, prev => {
    const counts = { ...prev.counts }
    if (counted) {
      const c = counts[counted.task] ?? { calls: 0, errors: 0 }
      counts[counted.task] = counted.phase === 'running' ? { ...c, calls: c.calls + 1 }
        : counted.phase === 'error' ? { ...c, errors: c.errors + 1 } : c
    }
    return { events: change(prev.events).slice(-MAX_EVENTS), counts, now }
  })
  isDirty = true
  void flushActivity($)
}

/** Send the latest activity to the running dashboard; one request at a time, coalescing bursts. */
async function flushActivity($: EngineInterface) {
  if (posting) { postAgain = true; return }
  posting = true
  try {
    do {
      postAgain = false
      const target = live
      if (!target) return
      const { events } = await read($, activity)
      if (!events.length) return
      const body = JSON.stringify({ events: events.slice(-MAX_EVENTS).map(e => ({
        id: e.id, task: e.task, tool: e.tool, target: e.target, phase: e.phase,
        started_at: e.startedAt, ended_at: e.endedAt, agent: e.agent, via: e.via,
      })) })
      await $.http.fetch(`http://127.0.0.1:${target.port}/api/activity`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Board-Token': target.token }, body,
      }).catch(() => undefined)
    } while (postAgain)
  } finally {
    posting = false
  }
}

async function summarize($: EngineInterface, force = false) {
  const target = live
  const settings = await read($, ai)
  if (!target || !settings.isEnabled || isSummarizing) return
  const now = await $.clock.now()
  if (!force && (!isDirty || now - lastSummaryAt < SUMMARY_GAP_MS)) return
  const b = await read($, board)
  if (!b || b.runId !== target.runId) return
  isSummarizing = true
  isDirty = false
  lastSummaryAt = now
  await update($, ai, prev => ({ ...prev, phase: 'running' }))
  try {
    const messages = await $.session.messages()
    const records = {
      goal: b.goal,
      tasks: b.tasks.map(t => ({ id: t.id, title: t.title, status: t.status, depends_on: t.dependsOn, checks: t.checks })),
      decisions: b.decisions.map(d => ({ id: d.id, status: d.status, question: clip(d.question, 80) })),
    }
    const prompt = JSON.stringify({ records, activity: activityDigest(messages) })
    const reply = await $.model.complete({ model: 'haiku', effort: 'low', maxTokens: 1200, system: SUMMARY_SYSTEM, prompt })
    if (!reply.isAnswered) throw new Error(`Haiku 응답 없음: ${reply.reason}`)
    const parsed = parseSummary(reply.text)
    if (!parsed) throw new Error('Haiku 응답을 JSON으로 읽지 못했습니다')
    const tokens = reply.usage.input_tokens + reply.usage.output_tokens
    const body = JSON.stringify({ ...parsed, model: 'haiku', generated_at: new Date(now).toISOString(), usage_tokens: tokens })
    const posted = await $.http.fetch(`http://127.0.0.1:${target.port}/api/session`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Board-Token': target.token }, body,
    })
    if (!posted.ok) throw new Error(`대시보드가 요약을 거절했습니다 (${posted.status})`)
    await update($, ai, prev => ({ ...prev, phase: 'idle', lastAt: now, tokens, error: undefined }))
  } catch (error) {
    await update($, ai, prev => ({ ...prev, phase: 'error', error: clip(error instanceof Error ? error.message : String(error), 140) }))
  } finally {
    isSummarizing = false
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    // A reload ends the previous server process; drop its stale address.
    await update($, server, () => ({ phase: 'off' }))
    await update($, ai, prev => ({ ...prev, phase: 'idle' }))
    await $.command.register({ name: 'guided-board', description: 'guided-execution 할 일 패널 열기' })
    await refresh($)
    $.clock.every(POLL_MS, () => {
      void refresh($).then(async () => {
        const b = await read($, board)
        if (b?.tasks.some(t => t.status === 'running')) {
          const now = await $.clock.now()
          await update($, activity, prev => ({ ...prev, now }))
        }
        return summarize($)
      })
    })
    return started
  })

  on('command.run', { command: 'guided-board' }, async $ => {
    await refresh($)
    await $.ui.open({ id: PANE, title: 'Guided 할 일' })
    const b = await read($, board)
    return { text: b ? summaryLine(b) : 'guided-execution 실행 기록 없음' }
  })

  // Observe only: every call runs unchanged; its metadata (tool, target, outcome) joins a node.
  on('tool.call', async ($, e, next) => {
    let event: ActivityEvent | undefined
    try {
      const b = await read($, board)
      if (b && b.tasks.length && !b.isComplete) {
        const root = await $.session.root()
        const input = e as unknown as Record<string, unknown>
        const owner = attribute(e.tool, input, b, root, agentTasks, e.agentId)
        const startedAt = await $.clock.now()
        event = {
          id: e.tool_use_id ?? `${e.tool}-${startedAt}-${Math.random().toString(36).slice(2, 6)}`,
          task: owner.task, via: owner.via, tool: e.tool, target: targetOf(e.tool, input, root),
          phase: 'running', startedAt, ...(e.agentId ? { agent: e.agentId } : {}),
        }
        const added = event
        await track($, events => [...events, added], added)
      }
    } catch { event = undefined }
    const result = await next(e)
    if (event) {
      const id = event.id
      const failed = 'deny' in result && result.deny !== undefined || ('isError' in result && result.isError === true)
      const done = await $.clock.now().catch(() => Date.now())
      const ended: ActivityEvent = { ...event, phase: failed ? 'error' : 'ok', endedAt: done }
      await track($, events => events.map(x => (x.id === id ? ended : x)), failed ? ended : undefined).catch(() => undefined)
    }
    return result
  })

  // A subagent started while one task runs (or whose prompt names one running task) works for that task.
  on('agent.spawn', async ($, e, next) => {
    const result = await next(e)
    try {
      const agentId = 'agentId' in result ? result.agentId : undefined
      const b = await read($, board)
      if (agentId && b) {
        const running = b.tasks.filter(t => t.status === 'running')
        const named = running.filter(t => new RegExp(`(^|[^a-z0-9_-])${t.id}([^a-z0-9_-]|$)`).test(e.prompt))
        const owner = running.length === 1 ? running[0] : named.length === 1 ? named[0] : undefined
        if (owner) agentTasks.set(agentId, owner.id)
      }
    } catch { /* attribution is best effort */ }
    return result
  })

  on('turn.complete', async ($, e, next) => {
    isDirty = true
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const b = await read($, board)
    if (!b || !b.tasks.length || b.isComplete || e.props.hasSurvey) return next(e)
    const { Box, Button, Text } = $.ui.resolve(e)
    return (
      <Box>
        <Text color="claude">▸ </Text>
        <Text wrap="truncate-end">{summaryLine(b, (await read($, activity)).events)} </Text>
        <Button key="open-board" plain dimColor label="할 일 보기" onPress={() => void $.ui.open({ id: PANE, title: 'Guided 할 일' })} />
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Link, Text } = $.ui.resolve(e)
    const b = await read($, board)
    const mode = await read($, view)
    const srv = await read($, server)
    const summary = await read($, ai)
    const act = await read($, activity)
    if (!b) {
      return (
        <Box flexDirection="column">
          <Text dimColor>guided-execution 실행 기록 없음</Text>
        </Box>
      )
    }
    const passed = b.tasks.filter(t => t.status === 'passed').length
    const byDecision = new Map(b.decisions.map(d => [d.id, d]))
    const isMine = srv.runId === b.runId
    return (
      <Box flexDirection="column">
        <Text bold wrap="truncate-end">{b.runId} · 통과 {passed}/{b.tasks.length}</Text>
        {b.goal ? <Text dimColor wrap="truncate-end">{b.goal}</Text> : null}
        {b.error ? <Text color="warning" wrap="truncate-end">기록 읽기 불일치 · 다시 읽는 중 · {b.error}</Text> : null}
        <Box flexDirection="row" flexWrap="wrap" columnGap={1} marginTop={1}>
          <Button key="view-list" hotkey="1" variant={mode === 'list' ? 'primary' : 'secondary'} label="목록" onPress={() => update($, view, () => 'list')} />
          <Button key="view-graph" hotkey="2" variant={mode === 'graph' ? 'primary' : 'secondary'} label="관계" onPress={() => update($, view, () => 'graph')} />
          {srv.phase === 'on' && isMine
            ? <Button key="web-stop" hotkey="w" label="웹 대시보드 닫기" onPress={() => stopServer($)} />
            : <Button key="web-open" hotkey="w" variant="secondary" label={srv.phase === 'starting' ? '웹 대시보드 여는 중…' : '웹 대시보드 열기'} onPress={() => startServer($)} />}
        </Box>
        {srv.phase === 'on' && isMine && srv.url ? (
          <Box flexDirection="column" marginTop={1}>
            <Link href={srv.url} label="대시보드 열기" />
            <Box flexDirection="row" columnGap={1}>
              <Text dimColor>
                Haiku 요약 {summary.isEnabled ? (summary.phase === 'running' ? '정리 중' : summary.lastAt ? `갱신됨${summary.tokens ? ` · 토큰 ${summary.tokens}` : ''}` : '대기') : '꺼짐'}
              </Text>
              <Button key="ai-toggle" plain dimColor label={summary.isEnabled ? '끄기' : '켜기'} onPress={() => update($, ai, prev => ({ ...prev, isEnabled: !prev.isEnabled }))} />
            </Box>
            {summary.phase === 'error' && summary.error ? <Text color="warning">{summary.error}</Text> : null}
          </Box>
        ) : null}
        {srv.phase === 'error' && isMine ? <Text color="error">대시보드를 열지 못했습니다: {srv.error}</Text> : null}
        <Box flexDirection="column" marginTop={1}>
          {mode === 'list'
            ? b.tasks.map(t => (
              <Box key={`t-${t.id}`} flexDirection="column">
                <Text color={tone(t.status)} wrap="truncate-end">
                  {GLYPH[t.status] ?? '○'} {t.title} <Text dimColor>{label(t.status)} · {t.attempts}/{t.maxAttempts}{b.ready.includes(t.id) ? ' · 준비됨' : ''}</Text>
                </Text>
                {t.checks.map(c => (
                  <Text key={`c-${t.id}-${c.id}`} color={tone(c.result)} dimColor={c.result === 'unrecorded'} wrap="truncate-end">
                    {'   '}{c.result === 'passed' ? '✓' : c.result === 'failed' ? '✗' : '○'} {c.id} {label(c.result)}
                  </Text>
                ))}
                {t.decisionIds.filter(d => !satisfied(byDecision.get(d))).map(d => (
                  <Text key={`d-${t.id}-${d}`} color="warning" wrap="truncate-end">{'   '}⏸ 결정 대기: {d}</Text>
                ))}
                {t.blockReason ? <Text color="warning" wrap="truncate-end">{'   '}차단 사유: {t.blockReason}</Text> : null}
                {liveRows(t, act, t.status === 'running' ? 3 : 1).map((row, i) => (
                  <Text key={`l-${t.id}-${i}`} color={row.color} dimColor={row.dim} wrap="truncate-end">{'   '}{row.text}</Text>
                ))}
              </Box>
            ))
            : relationRows(b, act).map((row, i) => (
              <Text key={`r-${i}`} color={row.color} dimColor={row.dim} wrap="truncate-end">{row.text}</Text>
            ))}
        </Box>
        {act.events.some(e => e.task === SESSION) ? (
          <Box flexDirection="column" marginTop={1}>
            <Text dimColor>세션 · 작업 밖 활동</Text>
            {liveRows({ id: SESSION, status: 'session' }, act, 2).map((row, i) => (
              <Text key={`s-${i}`} color={row.color} dimColor={row.dim} wrap="truncate-end">{'   '}{row.text}</Text>
            ))}
          </Box>
        ) : null}
        {b.otherRuns.length ? (
          <Box flexDirection="row" flexWrap="wrap" columnGap={1} marginTop={1}>
            <Text dimColor>다른 실행:</Text>
            {b.otherRuns.slice(0, 6).map(name => (
              <Button key={`run-${name}`} plain dimColor label={name} onPress={() => update($, pinnedRun, () => name)} />
            ))}
          </Box>
        ) : null}
      </Box>
    )
  })
}
