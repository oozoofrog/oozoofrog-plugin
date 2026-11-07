import { atom, read, update } from 'claude-code'
import type { Hook, Register } from 'claude-code'

import type { Call, Live, Modes, Place } from '../types'

const PANE = 'mac-cu-modes'
const TITLE = 'mac-cu'
const PREFIX = 'mcp__mac-cu__'
const modes = atom({ plugin: 'mac-computer-use', key: 'modes' } as const, { input: 'auto', show: 'glow' })
const place = atom({ plugin: 'mac-computer-use', key: 'place' } as const, 'band')
const calls = atom({ plugin: 'mac-computer-use', key: 'calls' } as const, [])
const live = atom({ plugin: 'mac-computer-use', key: 'live' } as const, null)
const allowed = atom({ plugin: 'mac-computer-use', key: 'allowed' } as const, [])

type Api = Parameters<Hook<'session.start'>>[0]

/** The values of each mode as mac-cu takes them, the default first, with what each does. */
const CHOICES: { mode: keyof Modes; label: string; values: [string, string][] }[] = [
  {
    mode: 'input',
    label: '조작 방식',
    values: [
      ['auto', '앱을 뒤에 둔 채 조작하고, 그래도 안 될 때만 앞으로 가져옵니다'],
      ['background', '항상 뒤에서만 조작합니다. 앞으로 가져오지 않습니다'],
      ['foreground', '매번 앱을 앞으로 가져와 실제 마우스·키보드로 조작합니다'],
    ],
  },
  {
    mode: 'show',
    label: '작업 표시',
    values: [
      ['glow', '조작하는 창에 빛과 포인터를 보여 줍니다'],
      ['steps', '빛·포인터와 함께 목표와 지금 단계를 창 아래에 보여 줍니다'],
      ['off', '아무것도 표시하지 않습니다'],
    ],
  },
]

const TOOLS: Record<string, string> = {
  act: '앱 조작',
  get_app_state: '창 읽기',
  browser: '브라우저',
  simulator: '시뮬레이터',
  webinspector: '웹 인스펙터',
  decide: '판단',
}

/** Where a call worked and what it did, from its input. */
function describe(tool: string, input: Record<string, unknown>): Pick<Call, 'target' | 'detail' | 'steps'> {
  const text = (key: string) => (typeof input[key] === 'string' ? (input[key] as string) : '')
  const actions = Array.isArray(input.actions) ? input.actions.length : 0
  switch (tool) {
    case 'act':
      return { target: text('app'), detail: text('goal'), steps: actions }
    case 'get_app_state':
      return { target: text('app'), detail: input.screenshot ? '트리·스크린샷' : '트리', steps: 0 }
    case 'browser':
      return { target: text('engine') || 'apple_events', detail: [text('action'), text('url')].filter(Boolean).join(' '), steps: 0 }
    case 'simulator':
      return { target: text('device') || '시뮬레이터', detail: [text('action'), text('target')].filter(Boolean).join(' '), steps: 0 }
    case 'webinspector':
      return { target: text('page') || '웹뷰', detail: text('action'), steps: 0 }
    default:
      return { target: text('app') || text('page'), detail: text('pick') || '질문', steps: 0 }
  }
}

const clock = (at: number) => {
  const d = new Date(at)
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map(n => String(n).padStart(2, '0')).join(':')
}
const seconds = (ms: number) => (ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`)
const facts = (...parts: (string | false)[]) => parts.filter(Boolean).join(' · ')
const MARK = { run: '●', ok: '✓', fail: '✗' } as const
const TONE = { run: 'claude', ok: 'success', fail: 'error' } as const

let modesFile = ''

async function setMode($: Api, mode: keyof Modes, value: string) {
  // Keep any other key mac-cu has in the file.
  const saved = await $.fs.read(modesFile).then(text => JSON.parse(text) as Record<string, string>, () => ({}))
  await $.fs.write(modesFile, JSON.stringify({ ...saved, [mode]: value }))
  await update($, modes, was => ({ ...was, [mode]: value }))
}

/** Shows the panel in the band or the pane, and keeps the choice for later sessions. */
async function move($: Api, to: Place) {
  if (to === 'pane') {
    const opened = await $.ui.open({ id: PANE, title: TITLE })
    if (!opened.isPlaced) {
      $.ui.toast(`옆 패널을 열 수 없어 입력창 위에 둡니다 (${opened.reason})`)
      to = 'band'
    }
  } else {
    await $.ui.close({ id: PANE })
  }
  await update($, place, () => to)
  await $.store.set('place', to)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const home = await $.env.get('HOME')
    const tmp = (await $.env.get('TMPDIR')) ?? '/tmp/'
    const folder = `${home}/Library/Application Support/mac-cu`
    const statusFolder = `${tmp.endsWith('/') ? tmp : tmp + '/'}mac-cu-status`
    modesFile = `${folder}/modes.json`
    const load = async () => {
      // A missing file or value is mac-cu's default, as `mac-cu --mode` prints it.
      const saved = await $.fs.read(modesFile).then(text => JSON.parse(text) as Partial<Modes>, () => ({}) as Partial<Modes>)
      const now: Modes = { input: saved.input ?? 'auto', show: saved.show ?? 'glow' }
      await update($, modes, was => (was.input === now.input && was.show === now.show ? was : now))

      // mac-cu keeps the step of act for 6 seconds (focus-overlay's macCUStep).
      // The files are per app, shared by every session: show one only while this session's act runs, with its goal.
      const running = new Set((await read($, calls)).filter(c => c.tool === 'act' && c.state === 'run').map(c => c.detail))
      const at = await $.clock.now()
      const fresh = running.size
        ? (await $.fs.list(statusFolder).catch(() => []))
            .filter(f => f.name.endsWith('.json') && at - f.mtimeMs < 6000)
            .sort((a, b) => b.mtimeMs - a.mtimeMs)
        : []
      let step: Live = null
      for (const file of fresh) {
        const record = await $.fs
          .read(`${statusFolder}/${file.name}`)
          .then(t => JSON.parse(t) as { goal?: string; step?: string }, () => null)
        if (record?.step && running.has(record.goal ?? '')) {
          step = { goal: record.goal ?? '', step: record.step }
          break
        }
      }
      await update($, live, was => (was?.step === step?.step && was?.goal === step?.goal ? was : step))

      const list = await $.fs.read(`${folder}/always-allow.txt`).catch(() => '')
      // Bundle IDs without the vendor prefix that says little: com.apple.Notes → Notes, com.google.Chrome → google.Chrome.
      const apps = list
        .split('\n')
        .map(line => line.trim())
        .filter(line => line && !line.startsWith('#'))
        .map(line => line.replace(/^com\.(apple\.)?/, ''))
      await update($, allowed, was => (was.join() === apps.join() ? was : apps))
    }
    await load()
    $.clock.every(2000, () => void load())
    await $.command.register({ name: 'mac-cu-modes', description: 'mac-cu 표시 위치 바꾸기 (입력창 위 ↔ 옆 패널)' })
    if ((await $.store.get('place')) === 'pane') await move($, 'pane')

    return next(e)
  })

  on('command.run', { command: 'mac-cu-modes' }, async $ => {
    await move($, (await read($, place)) === 'pane' ? 'band' : 'pane')

    return { text: `mac-cu를 ${(await read($, place)) === 'pane' ? '옆 패널' : '입력창 위'}에 표시합니다.` }
  })

  // Every mac-cu call of this session, with its result and time.
  on('tool.call', async ($, e, next) => {
    if (!e.tool.startsWith(PREFIX)) return next(e)
    const tool = e.tool.slice(PREFIX.length)
    const call: Call = { id: e.tool_use_id, tool, ...describe(tool, e as Record<string, unknown>), state: 'run', at: await $.clock.now(), ms: 0 }
    await update($, calls, list => [...list, call].slice(-30))
    const finish = async (state: Call['state']) => {
      const ms = (await $.clock.now()) - call.at
      await update($, calls, list => list.map(one => (one.id === call.id ? { ...one, state, ms } : one)))
    }
    try {
      const ran = await next(e)
      await finish(ran.isError || ran.deny !== undefined ? 'fail' : 'ok')
      return ran
    } catch (error) {
      // A call that threw must not stay running in the band.
      await finish('fail')
      throw error
    }
  })

  // Closing the pane by hand brings the panel back above the prompt.
  on('ui.close', async ($, e, next) => {
    const closed = await next(e)
    if (e.id === PANE && e.origin.kind === 'person') {
      await update($, place, () => 'band')
      await $.store.set('place', 'band')
    }

    return closed
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey || (await read($, place)) === 'pane') {
      return next(e)
    }
    const { Box, Button, Text } = $.ui.resolve(e)
    const now = await read($, modes)
    const step = await read($, live)
    const last = (await read($, calls)).at(-1)

    return (
      <Box gap={1} alignItems="center">
        <Text bold color="claude">mac-cu</Text>
        <Text dimColor>조작</Text>
        <Text>{now.input}</Text>
        <Text dimColor>· 표시</Text>
        <Text>{now.show}</Text>
        <Box flexGrow={1} flexShrink={1} minWidth={0}>
          {step ? (
            <Text wrap="truncate" color="claude">
              ● {step.goal ? `${step.goal} — ` : ''}{step.step}
            </Text>
          ) : last ? (
            <Text wrap="truncate" dimColor>
              │ <Text color={TONE[last.state]}>{MARK[last.state]}</Text> {facts(last.target, TOOLS[last.tool] ?? last.tool, last.detail, last.state !== 'run' && seconds(last.ms))}
            </Text>
          ) : (
            <Text wrap="truncate" dimColor>│ 이 세션에서 아직 쓰지 않았습니다</Text>
          )}
        </Box>
        <Button key="move" label="자세히 ⇥" onPress={() => move($, 'pane')} />
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const now = await read($, modes)
    const step = await read($, live)
    const list = await read($, calls)
    const apps = await read($, allowed)
    const failed = list.filter(c => c.state === 'fail').length
    const targets = new Set(list.map(c => c.target).filter(Boolean)).size

    return (
      <Box flexDirection="column" gap={1}>
        {step && (
          <Box flexDirection="column" borderStyle="round" borderColor="claude" paddingX={1}>
            <Text size="caption" color="claude">지금 진행 중</Text>
            {step.goal ? <Text weight="semibold">{step.goal}</Text> : null}
            <Text>{step.step}</Text>
          </Box>
        )}

        <Box flexDirection="column">
          <Text size="caption" dimColor>모드 · 누르면 바로 바뀝니다</Text>
          {CHOICES.map(choice => {
            const current = now[choice.mode]
            const about = choice.values.find(([value]) => value === current)?.[1] ?? ''
            return (
              <Box key={choice.mode} flexDirection="column" marginTop={1}>
                <Box gap={1} alignItems="center" flexWrap="wrap">
                  <Text weight="medium">{choice.label}</Text>
                  {choice.values.map(([value]) => (
                    <Button
                      key={`${choice.mode}-${value}`}
                      label={value}
                      variant={value === current ? 'primary' : 'secondary'}
                      onPress={() => setMode($, choice.mode, value)}
                    />
                  ))}
                </Box>
                <Text size="footnote" dimColor>{about}</Text>
              </Box>
            )
          })}
        </Box>

        <Box flexDirection="column">
          <Text size="caption" dimColor>
            이 세션의 작업 · {list.length}회{failed ? ` · 실패 ${failed}회` : ''}{targets ? ` · 대상 ${targets}곳` : ''}
          </Text>
          {list.length === 0 && <Text dimColor>아직 mac-cu를 쓰지 않았습니다.</Text>}
          {list
            .slice(-8)
            .reverse()
            .map(c => (
              <Box key={c.id} gap={1}>
                <Text color={TONE[c.state]}>{MARK[c.state]}</Text>
                <Text tabular dimColor>{clock(c.at)}</Text>
                <Box flexDirection="column" flexShrink={1} minWidth={0}>
                  <Text wrap="truncate">
                    <Text weight="medium">{c.target || '—'}</Text> · {TOOLS[c.tool] ?? c.tool}
                  </Text>
                  <Text size="footnote" dimColor wrap="truncate">
                    {facts(c.detail, c.steps > 0 && `${c.steps}단계`, c.state !== 'run' && seconds(c.ms)) || '…'}
                  </Text>
                </Box>
              </Box>
            ))}
        </Box>

        {apps.length > 0 && (
          <Box flexDirection="column">
            <Text size="caption" dimColor>항상 허용한 앱 · {apps.length}개</Text>
            <Text size="footnote" wrap="wrap">{apps.join(' · ')}</Text>
          </Box>
        )}

        <Button key="move" label="입력창 위로" onPress={() => move($, 'band')} />
      </Box>
    )
  })
}
