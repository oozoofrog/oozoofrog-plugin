export type CheckResult = 'passed' | 'failed' | 'not_run' | 'unrecorded' | 'stale' | 'mixed'

export type BoardCheck = { id: string; result: CheckResult }

export type BoardTask = {
  id: string
  title: string
  status: string
  attempts: number
  maxAttempts: number
  dependsOn: string[]
  decisionIds: string[]
  blockReason?: string
  checks: BoardCheck[]
  isRetried: boolean
}

export type BoardDecision = {
  id: string
  kind: string
  question: string
  status: string
  outcome?: string
}

export type Board = {
  runId: string
  workspace: string
  goal: string
  tasks: BoardTask[]
  decisions: BoardDecision[]
  ready: string[]
  isComplete: boolean
  readAt: number
  otherRuns: string[]
  error?: string
}

export type View = 'list' | 'graph'

export type ServerState = {
  phase: 'off' | 'starting' | 'on' | 'error'
  url?: string
  runId?: string
  error?: string
}

export type AiState = {
  isEnabled: boolean
  phase: 'idle' | 'running' | 'error'
  lastAt?: number
  tokens?: number
  error?: string
}

declare module 'claude-code' {
  interface PluginState {
    'guided-execution': {
      board: Shaped<Board | null>
      view: Shaped<View>
      server: Shaped<ServerState>
      ai: Shaped<AiState>
      pinnedRun: Shaped<string>
      autoOpenedRun: Shaped<string>
    }
  }
}
