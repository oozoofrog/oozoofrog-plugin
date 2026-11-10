import { expect, mock, test } from 'claude-code/testing'

import { SESSION, attribute, liveRows, parseSummary, relationRows, summaryLine, targetOf, toBoard } from './register'

const PLAN = {
  schema_version: 1,
  goal: '노트 내보내기',
  decisions: [{ id: 'format', kind: 'direction', question: '형식?' }],
  tasks: [
    { id: 'export', title: '내보내기 구현', depends_on: [], decision_ids: [], max_attempts: 3,
      checks: [{ id: 'behavior', description: 'roundtrip' }] },
    { id: 'usage', title: '사용법 문서', depends_on: ['export'], decision_ids: ['format'], max_attempts: 3,
      checks: [{ id: 'example', description: 'doc run' }] },
  ],
}
const STATE = {
  run_id: 'notes',
  tasks: {
    export: { status: 'passed', attempts: 2, evidence: [{ check_id: 'behavior', result: 'passed' }] },
    usage: { status: 'pending', attempts: 0, evidence: [] },
  },
  decisions: { format: { status: 'pending' } },
  history: [{ action: 'start', previous_tasks: { export: { status: 'failed', attempts: 1 } } }],
}

const PANE = {
  plugin: 'guided-execution',
  component: 'Pane',
  requestId: 'guided-board',
  props: {
    title: 'Guided 할 일', isFocused: false, bodyColumns: 60, placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 }, view: {},
  },
} as const

const BAND = {
  plugin: 'guided-execution',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false, isCollapsed: false, isWorking: false, maxRows: 6, bodyColumns: 100,
    scroll: { offset: 0, bodyRows: 6 }, view: {},
  },
} as const

function engine(on: Parameters<Parameters<typeof test>[1]>[1], state: object = STATE) {
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.root', () => ({ value: '/p' }))
  on('command.register', () => ({ value: { command: 'guided-board' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('fs.exists', () => ({ value: true }))
  on('fs.list', () => ({ value: [{ name: 'notes', kind: 'dir', size: 0, mtimeMs: 0, isLink: false }] }))
  on('fs.stat', () => ({ value: { kind: 'file', size: 10, mtimeMs: 5, isLink: false } }))
  on('fs.read', (_, e) => ({
    value: e.path.endsWith('plan.json') ? JSON.stringify(PLAN) : JSON.stringify(state),
  }))
}

test('records become a board: ready work, gates, retries', async () => {
  const b = toBoard('notes', '/p/.agent-loop/notes', JSON.stringify(PLAN), JSON.stringify(STATE), 0)
  expect(b.ready).toEqual([])
  expect(b.tasks[0]?.isRetried).toBe(true)
  expect(b.tasks[1]?.checks[0]?.result).toBe('unrecorded')
  expect(summaryLine(b)).toBe('notes · 통과 1/2 · 결정 대기 1')
  const rows = relationRows(b).map(r => r.text)
  expect(rows).toContain('export ──▶ usage  [대기]')
  expect(rows).toContain('   ◆ format ═▶ usage  (결정 대기)')
  expect(rows).toContain('   ↺ export 실패 후 재시작 기록')
})

test('a plan and state that disagree are refused, not drawn', async () => {
  const torn = { ...STATE, tasks: { export: STATE.tasks.export } }
  expect(() => toBoard('notes', '/x', JSON.stringify(PLAN), JSON.stringify(torn), 0)).toThrow()
})

test('a summary reply is read only when it holds stages', async () => {
  expect(parseSummary('```json\n{"stages":[{"id":"a","label":"b"}]}\n```')?.stages).toEqual([{ id: 'a', label: 'b' }])
  expect(parseSummary('no json here')).toBe(undefined)
  expect(parseSummary('{"headline":"x"}')).toBe(undefined)
})

test('the pane lists tasks and switches to relations, on every surface', async ($, on) => {
  mock.clock(on, { now: 1_000_000 })
  engine(on)
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /notes · 통과 1\/2/ }))?.text).toBe('notes · 통과 1/2')
    expect(await ui.find({ type: 'Text', text: /결정 대기: format/ })).toBeTruthy()
    await ui.press({ key: 'view-graph' })
    expect(await ui.find({ type: 'Text', text: /◆ format ═▶ usage/ })).toBeTruthy()
    await ui.press({ key: 'view-list' })
    await ui.unmount()
  }
})

test('the band shows one line while work remains and steps aside when done', async ($, on) => {
  mock.clock(on, { now: 1_000_000 })
  engine(on)
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /통과 1\/2/ }))?.text).toBe('notes · 통과 1/2 · 결정 대기 1 ')
  await ui.unmount()
})

test('no records: the pane says so and offers no dashboard', async ($, on) => {
  mock.clock(on, { now: 1_000_000 })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.root', () => ({ value: '/empty' }))
  on('command.register', () => ({ value: { command: 'guided-board' } }))
  on('fs.exists', () => ({ value: false }))
  await $.session.start({ cwd: '/empty', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /실행 기록 없음/ })).toBeTruthy()
  expect(await ui.find({ type: 'Button', key: 'web-open' })).toBeFalsy()
  await ui.unmount()
})

test('the dashboard press starts the server, opens it, and sends a Haiku summary of labels only', async ($, on) => {
  const clock = mock.clock(on, { now: 1_000_000 })
  mock.env(on, {})
  engine(on)
  const opened: string[][] = []
  const posted: { url: string; headers: Record<string, string>; body: string }[] = []
  let prompt = ''
  on('process.spawn', async function* (_, e) {
    expect(e.argv.slice(-2)).toEqual(['--workspace', '/p/.agent-loop/notes'])
    yield { stream: 'stdout', text: '{"url":"http://127.0.0.1:4567/?t=tok","port":4567,' }
    yield { stream: 'stdout', text: '"token":"tok"}\n' }
    await clock.sleep(60_000)
    return { code: 0, signal: null }
  })
  on('process.run', (_, e) => {
    opened.push([...e.argv])
    return { value: { exitCode: 0, stdout: '', stderr: '' } }
  })
  on('session.messages', () => ({
    value: [{ role: 'user', text: '내보내기 만들어줘', toolUses: [] },
      { role: 'assistant', text: '', toolUses: [{ tool_use_id: 't1', tool: 'Bash', input: { command: 'pytest -q' }, text: 'SECRET OUTPUT' }] }],
  }))
  on('model.complete', (_, e) => {
    expect(e.model).toBe('haiku')
    prompt = typeof e.prompt === 'string' ? e.prompt : ''
    return { value: { isAnswered: true, text: '{"headline":"문서화 대기","stages":[{"id":"s1","label":"구현","refs":["export"]}]}',
      usage: { input_tokens: 300, output_tokens: 60, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 } } }
  })
  on('http.fetch', (_, e) => {
    posted.push({ url: e.url, headers: { ...(e.init?.headers ?? {}) }, body: typeof e.init?.body === 'string' ? e.init.body : '' })
    return { value: { status: 200, ok: true, headers: {}, text: '{"ok":true}' } }
  })
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'web-open' })
  await clock.settle()
  expect(opened[0]).toEqual(['open', 'http://127.0.0.1:4567/?t=tok'])
  expect(await ui.find({ type: 'Button', key: 'web-stop' })).toBeTruthy()

  await clock.advance(2_000)
  expect(posted.length).toBe(1)
  expect(posted[0]?.url).toBe('http://127.0.0.1:4567/api/session')
  expect(posted[0]?.headers['X-Board-Token']).toBe('tok')
  const sent = JSON.parse(posted[0]?.body ?? '{}')
  expect(sent.model).toBe('haiku')
  expect(sent.usage_tokens).toBe(360)
  expect(prompt.includes('pytest -q')).toBe(true)
  expect(prompt.includes('SECRET OUTPUT')).toBe(false)

  await ui.press({ key: 'ai-toggle' })
  await clock.advance(30_000)
  expect(posted.length).toBe(1)
  await ui.unmount()
})

const RUNNING = {
  ...STATE,
  tasks: {
    export: { status: 'passed', attempts: 2, evidence: [{ check_id: 'behavior', result: 'passed' }] },
    usage: { status: 'running', attempts: 1, evidence: [], running_revision: 'r1' },
  },
  decisions: { format: { status: 'resolved', outcome: 'answered', answer: 'json' } },
  history: [...STATE.history, { action: 'start', task: 'usage', timestamp: '1970-01-01T00:16:00Z',
    previous_tasks: { usage: { status: 'pending', attempts: 0 } } }],
}
const PLAN_SCOPES = {
  ...PLAN,
  tasks: PLAN.tasks.map(t => ({ ...t, reads: ['src'], writes: [t.id === 'export' ? 'src/export.py' : 'README.md'] })),
}

test('tool calls go to the named, the only running, or the one in-scope task; else the session', async () => {
  const one = toBoard('notes', '/p/.agent-loop/notes', JSON.stringify(PLAN_SCOPES), JSON.stringify(RUNNING), 0)
  const none = new Map<string, string>()
  expect(attribute('Read', { file_path: '/p/x' }, one, '/p', none)).toEqual({ task: 'usage', via: 'running' })
  expect(attribute('Bash', { command: 'python3 s/loop_control.py finish --workspace .agent-loop/notes --task export' }, one, '/p', none))
    .toEqual({ task: 'export', via: 'command' })
  expect(attribute('Bash', { command: 'python3 loop_control.py start --workspace .agent-loop/other --task export' }, one, '/p', none).task)
    .toBe('usage')
  const both = { ...one, tasks: one.tasks.map(t => ({ ...t, status: 'running' })) }
  expect(attribute('Edit', { file_path: '/p/src/export.py' }, both, '/p', none)).toEqual({ task: 'export', via: 'scope' })
  expect(attribute('Edit', { file_path: '/p/README.md' }, both, '/p', none)).toEqual({ task: 'usage', via: 'scope' })
  expect(attribute('Read', { file_path: '/p/src/other.py' }, both, '/p', none)).toEqual({ task: SESSION, via: 'ambiguous' })
  expect(attribute('Read', { file_path: '/p/src/other.py' }, both, '/p', new Map([['ag1', 'export']]), 'ag1'))
    .toEqual({ task: 'export', via: 'agent' })
  const idle = { ...one, tasks: one.tasks.map(t => ({ ...t, status: 'pending' })) }
  expect(attribute('Grep', { pattern: 'x' }, idle, '/p', none)).toEqual({ task: SESSION, via: 'idle' })
  expect(targetOf('Read', { file_path: '/p/src/a.ts' }, '/p')).toBe('src/a.ts')
  expect(targetOf('Bash', { command: 'rm -rf x', description: '정리' }, '/p')).toBe('정리')
})

test('records give a running node its start time and last transition', async () => {
  const b = toBoard('notes', '/x', JSON.stringify(PLAN_SCOPES), JSON.stringify(RUNNING), 0)
  const usage = b.tasks[1]!
  expect(usage.startedAt).toBe(960_000)
  expect(usage.lastRecord).toBe('시작')
  expect(usage.writes).toEqual(['README.md'])
  const rows = liveRows(usage, { now: 1_000_000, counts: { usage: { calls: 2, errors: 1 } }, events: [
    { id: 'a', task: 'usage', tool: 'Read', target: 'README.md', phase: 'ok', startedAt: 990_000, endedAt: 990_300, via: 'running' },
    { id: 'b', task: 'usage', tool: 'Bash', target: '테스트', phase: 'error', startedAt: 991_000, endedAt: 993_000, via: 'running' },
    { id: 'c', task: 'usage', tool: 'Grep', target: 'TODO', phase: 'running', startedAt: 998_000, via: 'running' },
  ] }).map(r => r.text)
  expect(rows).toEqual(['◌ Grep TODO · 2.0s', '✗ Bash 테스트 · 2.0s', '● Read README.md · 0.3s', '경과 00:40 · 도구 2 · 오류 1 · 기록: 시작'])
})

test('an observed tool call runs unchanged and shows on its task in the pane and band', async ($, on) => {
  const clock = mock.clock(on, { now: 1_000_000 })
  engine(on, RUNNING)
  const ran: unknown[] = []
  on('tool.call', (_, e) => { ran.push(e); return { result: { ok: true } } as never })
  await $.session.start({ cwd: '/p', surface: 'terminal', isInteractive: true })
  const result = await $.tool.call({ tool: 'Read', file_path: '/p/README.md' } as never)
  expect(ran.length).toBe(1)
  expect('result' in result).toBe(true)
  await clock.advance(2_000)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /● Read README.md/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /경과 00:42 · 도구 1/ })).toBeTruthy()
  await ui.unmount()
})
