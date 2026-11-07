/** mac-cu's modes as `mac-cu --mode` prints them. */
export type Modes = { input: string; show: string }
/** Where the mod shows them: the band above the prompt, or a pane beside the chat. */
export type Place = 'band' | 'pane'
/** One mac-cu tool call of this session. */
export type Call = {
  id: string
  /** The tool's name without `mcp__mac-cu__`. */
  tool: string
  /** The app, browser engine, simulator or page it worked on. */
  target: string
  /** The goal of an act, else what the call did. */
  detail: string
  steps: number
  state: 'run' | 'ok' | 'fail'
  at: number
  ms: number
}
/** What act does now (mac-cu writes it while show=steps), or null. */
export type Live = { goal: string; step: string } | null

declare module 'claude-code' {
  interface PluginState {
    'mac-computer-use': { modes: Modes; place: Place; calls: Call[]; live: Live; allowed: string[] }
  }
}
