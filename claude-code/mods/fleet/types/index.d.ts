/** A tool call as the pane names it. `key` groups repeats of the same command; `options` are a question's answers. */
export type Call = { tool: string; text: string; key: string; options?: string[] }

export type Sub = {
  name: string
  type: string
  model: string
  isBackground: boolean
  state: 'waiting' | 'working'
  pending: Call | null
  secs: number
}

export type Group = 'question' | 'permission' | 'finished' | 'working'

export type Session = {
  sessionId: string
  name: string
  kind: 'main' | 'bg'
  status: string
  waitingFor: string
  secs: number
  branch: string
  ctx: number
  /** Share of the repo's autoCompactWindow, and how many ctx.py BANDS it has crossed (0-3). */
  ctxPct: number
  ctxBand: number
  pending: Call[]
  last: string
  /** Seconds since the transcript's last user or assistant turn; null when unknown. */
  turnSecs: number | null
  /** Your custom Zed tab title, matched to this chat by name; empty when none matches. */
  tab: string
  /** Set by scan.py, which also sorts sessions: needs-you first, longest wait first. */
  group: Group
  subs: Sub[]
}

export type Handoff = { file: string; owner: string; secs: number }

export type Scan = { sessions: Session[]; handoffs: Handoff[] }

export type Counts = { question: number; permission: number }

declare module 'claude-code' {
  interface PluginState {
    fleet: {
      sessions: Session[]
      handoffs: Handoff[]
      isOpen: boolean
      scannedAt: number
      /** Section and row keys the person toggled away from their default. */
      toggled: string[]
    }
  }
}
