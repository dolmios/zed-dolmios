import { expect, mock, test } from 'claude-code/testing'

import type { Session } from '../types'

const base = { branch: 'development', ctx: 120000, ctxPct: 24, ctxBand: 0, last: '', subs: [], waitingFor: '', secs: 90, turnSecs: 30, tab: '' }
const bash = (text: string, key: string) => ({ tool: 'Bash', text, key })
const LIST: Session[] = [
  { ...base, sessionId: 'a', name: 'GH-3040-15Oct', kind: 'main', group: 'permission', status: 'waiting', pending: [bash('Commit GH-3040', 'Bash git merge-base')], ctxPct: 88, ctxBand: 3, tab: '3040' },
  {
    ...base, sessionId: 'b', name: 'oct15-design-pm', kind: 'main', group: 'permission', status: 'busy', pending: [],
    subs: [{ name: 'Audit B code quality', type: 'general-purpose', model: 'sonnet', isBackground: true, state: 'waiting', pending: bash('git merge-base', 'Bash git merge-base'), secs: 40 }],
  },
  { ...base, sessionId: 'd', name: 'W3b-stuck', kind: 'bg', group: 'permission', status: 'waiting', pending: [], turnSecs: 5100 },
  { ...base, sessionId: 'c', name: 'INT-kb', kind: 'bg', group: 'finished', status: 'idle', pending: [], last: 'Page list is drafted' },
]

for (const surface of ['terminal', 'desktop'] as const) {
  test(`pane groups sessions and names what each waits on (${surface})`, async ($, on) => {
    mock.env(on, { HOME: '/h' })
    const ticks: (() => void)[] = []
    on('session.start', async (_$, e) => e as never)
    on('command.register', async () => ({ value: undefined }) as never)
    on('clock.every', async (_$, e) => {
      ticks.push((e as unknown as { fn: () => void }).fn)
      return { value: {} } as never
    })
    on('fs.list', async () => ({ value: [] }) as never)
    on('clock.now', async () => ({ value: 0 }) as never)
    on('process.run', async (_$, e) => ({ value: { exitCode: 0, stdout: e.argv[0] === 'python3' ? JSON.stringify({ sessions: LIST, handoffs: [{ file: 'PM-15Oct.md', owner: 'PM-15Oct [cfc819]', secs: 90000 }] }) : '', stderr: '' } }) as never)
    on('ui.status', async () => ({ value: undefined }) as never)
    on('ui.open', async () => ({ value: { isPlaced: true } }) as never)

    await $.session.start({ cwd: '/h', surface, isInteractive: true })
    await $.command.run({ command: 'fleet', args: '' } as never)
    // A second session.start re-runs the tick, now with the pane open.
    await $.session.start({ cwd: '/h', surface, isInteractive: true })
    const tree = JSON.stringify(await $.ui.render({ surface, component: 'Pane', requestId: 'fleet', props: {} } as never))

    for (const text of ['Needs approval', 'Commit GH-3040', 'Audit B code quality', 'git merge-base', 'Finished', 'SUB ', 'MAIN ', ' (3040)', 'Same approval, several chats', 'Bash git merge-base ', '×2', 'no turn for 1h25m: check the chat', '───', 'refresh', 'live · ', '88% 1m', 'context 88%: /compact or hand off', 'Handoff files', 'row:a', 'sec:finished']) {
      expect(tree).toContain(text)
    }
    // Finished starts collapsed: its rows are not drawn.
    expect(tree).not.toContain('Page list is drafted')

    await ($.ui as unknown as { press: (a: object) => Promise<unknown> }).press({ plugin: 'fleet', key: 'sec:finished' })
    const opened = JSON.stringify(await $.ui.render({ surface, component: 'Pane', requestId: 'fleet', props: {} } as never))
    expect(opened).toContain('Page list is drafted')
    expect(opened).toContain('BG ')
  })
}
