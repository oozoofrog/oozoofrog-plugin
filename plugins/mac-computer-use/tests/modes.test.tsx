import { expect, mock, test } from 'claude-code/testing'

const SITE = { scroll: { offset: 0, bodyRows: 20 }, view: {} } as const
const BAND = {
  plugin: 'mac-computer-use',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 4, bodyColumns: 100, ...SITE },
} as const
const PANE = {
  plugin: 'mac-computer-use',
  component: 'Pane',
  requestId: 'mac-cu-modes',
  props: { title: 'mac-cu', isFocused: false, bodyColumns: 40, placement: 'dock', ...SITE },
} as const
const MODES = '/Users/me/Library/Application Support/mac-cu/modes.json'

test('the band shows the modes and the last mac-cu call; the pane changes a mode and moves back', async ($, on) => {
  const files = new Map<string, string>([[MODES, '{"input":"auto","place":"x","show":"steps"}']])
  const store = new Map<string, unknown>()
  const opened: string[] = []
  let now = 1_000_000
  on('env.get', (_, e) => ({ value: e.name === 'HOME' ? '/Users/me' : '/tmp/' }))
  on('fs.read', (_, e) => {
    const text = files.get(e.path)
    if (text === undefined) throw new Error('missing')
    return { value: text }
  })
  on('fs.write', (_, e) => (files.set(e.path, e.text), { value: undefined }))
  on('fs.list', () => ({ value: [] }))
  on('clock.now', () => ({ value: (now += 1200) }))
  on('clock.every', () => ({ value: undefined }))
  on('store.get', (_, e) => ({ value: store.get(e.key) }))
  on('store.set', (_, e) => (store.set(e.key, e.value), { value: undefined }))
  on('command.register', () => ({ value: { command: 'mac-cu-modes' } }))
  on('ui.open', (_, e) => (opened.push(e.id), { value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('tool.call', () => ({ result: {} }))
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))

  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect((await ui.find({ type: 'Text', text: 'steps' }))?.text).toBe('steps')
    expect((await ui.find({ type: 'Text', text: /아직/ }))?.text).toBe('│ 이 세션에서 아직 쓰지 않았습니다')
    await ui.unmount()
  }

  // Untyped: the MCP tool union is too deep for tsc here.
  const act: Record<string, unknown> = { tool: 'mcp__mac-cu__act', app: 'Notes', goal: '메모 정리', actions: [{ type: 'click', element: 1 }] }
  await ($.tool as unknown as { call: (input: unknown) => Promise<unknown> }).call(act)
  const band = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await band.find({ type: 'Text', text: /Notes/ }))?.text).toBe('│ ✓ Notes · 앱 조작 · 메모 정리 · 1.2s')
  await band.press({ key: 'move' })
  expect(opened).toEqual(['mac-cu-modes'])
  expect(store.get('place')).toBe('pane')
  await band.unmount()

  const pane = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await pane.find({ type: 'Text', text: /이 세션의 작업/ }))?.text).toBe('이 세션의 작업 · 1회 · 대상 1곳')
  await pane.press({ key: 'input-background' })
  // mac-cu's other keys stay in the file.
  expect(JSON.parse(files.get(MODES)!)).toEqual({ input: 'background', place: 'x', show: 'steps' })
  expect((await pane.find({ type: 'Text', text: /뒤에서만/ }))?.text).toBe('항상 뒤에서만 조작합니다. 앞으로 가져오지 않습니다')
  await pane.press({ key: 'move' })
  expect(store.get('place')).toBe('band')
  await pane.unmount()
})

test("the band shows only this session's act step, a call that threw as failed, and no commented apps", async ($, on) => {
  const STATUS = '/tmp/mac-cu-status'
  const files = new Map<string, string>([
    [`${STATUS}/1.json`, '{"goal":"다른 세션 일","step":"클릭 · 보내기"}'],
    [`${STATUS}/2.json`, '{"goal":"메모 정리","step":"입력 (3자)"}'],
    ['/Users/me/Library/Application Support/mac-cu/always-allow.txt', '# 내가 고른 앱\ncom.apple.Notes\n'],
  ])
  const clock = mock.clock(on)
  mock.store(on)
  let release = () => {}
  on('env.get', (_, e) => ({ value: e.name === 'HOME' ? '/Users/me' : '/tmp/' }))
  on('fs.read', (_, e) => {
    const text = files.get(e.path)
    if (text === undefined) throw new Error('missing')
    return { value: text }
  })
  // The other session's file is the newest.
  on('fs.list', () => ({
    value: [
      { name: '1.json', mtimeMs: Number.MAX_SAFE_INTEGER, kind: 'file' as const, size: 0, isLink: false },
      { name: '2.json', mtimeMs: Number.MAX_SAFE_INTEGER - 1, kind: 'file' as const, size: 0, isLink: false },
    ],
  }))
  on('command.register', () => ({ value: { command: 'mac-cu-modes' } }))
  on('tool.call', async (_, e) => {
    if ((e as { app?: string }).app === 'Mail') throw new Error('mac-cu stopped')
    await new Promise<void>(resolve => (release = resolve))
    return { result: {} }
  })
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })
  const call = ($.tool as unknown as { call: (input: unknown) => Promise<unknown> }).call

  const running = call({ tool: 'mcp__mac-cu__act', tool_use_id: 'a1', app: 'Notes', goal: '메모 정리', actions: [] })
  await clock.advance(2000)
  const band = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await band.find({ type: 'Text', text: /●/ }))?.text).toBe('● 메모 정리 — 입력 (3자)')
  await band.unmount()
  release()
  await running

  await expect(call({ tool: 'mcp__mac-cu__act', tool_use_id: 'a2', app: 'Mail', goal: '메일 보내기', actions: [] })).rejects.toThrow()
  await clock.advance(2000)
  const after = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await after.find({ type: 'Text', text: /Mail/ }))?.text).toMatch(/^│ ✗ Mail · 앱 조작 · 메일 보내기/)
  await after.unmount()

  const pane = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await pane.find({ type: 'Text', text: /항상 허용한 앱/ }))?.text).toBe('항상 허용한 앱 · 1개')
  await pane.unmount()
})
