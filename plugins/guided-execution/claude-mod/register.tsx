import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { AiState, Board, BoardCheck, BoardDecision, BoardTask, CheckResult, ServerState, View } from './types'

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
  for (const event of arr(state.history).map(obj)) {
    if (event.action !== 'start') continue
    for (const [name, prev] of Object.entries(obj(event.previous_tasks))) {
      if (obj(prev).status === 'failed') retried.add(name)
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

/** One line for the band: progress, what runs, what waits on the person. */
export function summaryLine(b: Board): string {
  const passed = b.tasks.filter(t => t.status === 'passed').length
  const running = b.tasks.filter(t => t.status === 'running').map(t => t.title)
  const waiting = b.decisions.filter(d => d.status === 'pending').length
  const blocked = b.tasks.filter(t => t.status === 'blocked').length
  const parts = [`${b.runId}`, `통과 ${passed}/${b.tasks.length}`]
  if (running.length) parts.push(`진행: ${clip(running.join(', '), 40)}`)
  else if (b.ready.length) parts.push(`다음: ${clip(b.tasks.find(t => t.id === b.ready[0])?.title, 32)}`)
  if (waiting) parts.push(`결정 대기 ${waiting}`)
  if (blocked) parts.push(`차단 ${blocked}`)
  if (b.error) parts.push('기록 읽기 불일치')
  return parts.join(' · ')
}

/** Relation view rows: prerequisites, decision gates, checks and recorded retries per task. */
export function relationRows(b: Board): { text: string; color?: string; dim?: boolean }[] {
  const rows: { text: string; color?: string; dim?: boolean }[] = []
  const byDecision = new Map(b.decisions.map(d => [d.id, d]))
  for (const t of b.tasks) {
    const from = t.dependsOn.length ? `${t.dependsOn.join(' + ')} ──▶ ` : ''
    rows.push({ text: `${from}${t.id}  [${label(t.status)}]`, color: tone(t.status) })
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
      void refresh($).then(() => summarize($))
    })
    return started
  })

  on('command.run', { command: 'guided-board' }, async $ => {
    await refresh($)
    await $.ui.open({ id: PANE, title: 'Guided 할 일' })
    const b = await read($, board)
    return { text: b ? summaryLine(b) : 'guided-execution 실행 기록 없음' }
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
        <Text wrap="truncate-end">{summaryLine(b)} </Text>
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
              </Box>
            ))
            : relationRows(b).map((row, i) => (
              <Text key={`r-${i}`} color={row.color} dimColor={row.dim} wrap="truncate-end">{row.text}</Text>
            ))}
        </Box>
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
