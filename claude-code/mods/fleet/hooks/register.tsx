import { atom, read, update } from 'claude-code'
import type { Register, RenderChildren } from 'claude-code'

import type { Call, Counts, Group, Handoff, Scan, Session, Sub } from '../types'

// Zero model tokens: every number here comes from local files.
// Cheap pass (every chat): status JSON only, feeds the status entry.
// Full pass (only while this chat's pane is open): scan.py reads transcript tails.
const PANE = 'fleet'
const TICK_MS = 3000
const STALE_MS = 2 * 3600 * 1000

const sessions = atom({ plugin: 'fleet', key: 'sessions' } as const, [])
const handoffs = atom({ plugin: 'fleet', key: 'handoffs' } as const, [])
const isOpen = atom({ plugin: 'fleet', key: 'isOpen' } as const, false)
const scannedAt = atom({ plugin: 'fleet', key: 'scannedAt' } as const, 0)
const toggled = atom({ plugin: 'fleet', key: 'toggled' } as const, [])

type Section = Group | 'repeats' | 'handoffs'
type StatusFile = { pid: number; status?: string; waitingFor?: string | null; updatedAt?: number }


const SECTION: Record<Section, { title: string; color: string; glyph: string; isOpenByDefault: boolean }> = {
  question: { title: 'Asking you', color: 'error', glyph: '?', isOpenByDefault: true },
  permission: { title: 'Needs approval', color: 'warning', glyph: '●', isOpenByDefault: true },
  finished: { title: 'Finished', color: 'success', glyph: '○', isOpenByDefault: false },
  working: { title: 'Working', color: 'inactive', glyph: '◌', isOpenByDefault: false },
  repeats: { title: 'Same approval, several chats', color: 'warning', glyph: '×', isOpenByDefault: true },
  handoffs: { title: 'Handoff files', color: 'text', glyph: '≡', isOpenByDefault: false },
}

// Same bands as the repo's context-watch hook: 50%, 70%, 85% of autoCompactWindow.
const BAND_COLOR = ['inactive', 'warning', 'warning', 'error']

const age = (secs: number) =>
  secs < 60 ? `${secs}s` : secs < 3600 ? `${Math.floor(secs / 60)}m` : `${Math.floor(secs / 3600)}h${Math.floor((secs % 3600) / 60)}m`
// The ui.press hook above does the toggling; the Button's own handler has nothing left to do.
const noop = () => undefined
// Set by session.start so a press of the refresh button can run the scan now.
let rescan: (() => Promise<unknown>) | undefined
const kindTag = (kind: string) => (kind === 'bg' ? 'BG  ' : 'MAIN')
// scan.py groups and sorts sessions; both views read its `group`.
const isNeedsYou = (s: Session) => s.group === 'question' || s.group === 'permission'
const QUIET_S = 600
const RULE = '─'.repeat(400)

/** The calls waiting on you right now: each chat's newest open call, plus every waiting subagent's. */
const waitingCalls = (list: Session[]) =>
  list.filter(isNeedsYou).flatMap(s => [
    ...(s.pending.length > 0 ? [{ call: s.pending[s.pending.length - 1]!, who: s.name }] : []),
    ...s.subs.flatMap(x => (x.state === 'waiting' && x.pending ? [{ call: x.pending, who: s.name }] : [])),
  ])

/** Commands two or more chats wait on: each is one allowlist rule away from clearing them all. */
const repeats = (list: Session[]) => {
  const byKey = new Map<string, string[]>()
  for (const { call, who } of waitingCalls(list)) byKey.set(call.key, [...(byKey.get(call.key) ?? []), who])

  return [...byKey.entries()].filter(([, who]) => who.length > 1).sort((a, b) => b[1].length - a[1].length)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'fleet', description: 'Show every local Claude session, the ones waiting on you first' })

    const home = await $.env.get('HOME')
    const dir = `${home}/.claude/sessions`
    const scanner = `${$.plugin.root}/scan.py`
    let isScanning = false

    const countWaiting = async (): Promise<Counts> => {
      const names = (await $.fs.list(dir)).filter(f => f.name.endsWith('.json')).map(f => f.name)
      const files = (
        await Promise.all(
          names.map(n => $.fs.read(`${dir}/${n}`).then(t => JSON.parse(t as string) as StatusFile).catch(() => undefined)),
        )
      ).filter((f): f is StatusFile => f !== undefined)
      // Session files of exited processes linger; one ps call keeps the live ones.
      const ps = files.length === 0 ? '' : (await $.process.run(['ps', '-o', 'pid=', '-p', files.map(f => f.pid).join(',')])).stdout
      const live = new Set(ps.split('\n').map(Number).filter(Boolean))
      const now = await $.clock.now()
      const waiting = files.filter(
        f => live.has(f.pid) && f.status === 'waiting' && now - (f.updatedAt ?? now) <= STALE_MS,
      )

      return {
        question: waiting.filter(f => f.waitingFor === 'input needed').length,
        permission: waiting.filter(f => f.waitingFor !== 'input needed').length,
      }
    }

    const scan = async () => {
      if (isScanning || !(await read($, isOpen))) return
      isScanning = true
      try {
        const run = await $.process.run(['python3', '-I', scanner])
        const scanned = JSON.parse(run.stdout) as Scan
        const fresh = scanned.sessions
        await update($, sessions, () => fresh)
        await update($, handoffs, () => scanned.handoffs)
        await update($, scannedAt, () => Date.now())
      } finally {
        isScanning = false
      }
    }

    const showCounts = async () => {
      const c = await countWaiting()
      await $.ui.status(c.question + c.permission === 0 ? undefined : `fleet: ${c.question} question · ${c.permission} permission`)
    }

    // The count and the scan fail on their own; one never blocks the other.
    const tick = () => Promise.allSettled([showCounts(), scan()])
    rescan = tick

    await tick().catch(() => undefined)
    $.clock.every(TICK_MS, () => void tick().catch(() => undefined))

    return next(e)
  })

  on('command.run', { command: 'fleet' }, async $ => {
    await update($, isOpen, () => true)
    await $.ui.open({ id: PANE, title: 'Fleet', columns: 72 })

    return { text: 'Fleet pane opened.' }
  })

  on('ui.close', async ($, e, next) => {
    if (e.id === PANE) await update($, isOpen, () => false)

    return next(e)
  })

  // Every section header and row is a Button keyed by what it opens; a press flips it.
  on('ui.press', { plugin: 'fleet' }, async ($, e, next) => {
    if (e.element === 'refresh') {
      await rescan?.()
      return next(e)
    }
    await update($, toggled, list => (list.includes(e.element) ? list.filter(k => k !== e.element) : [...list, e.element]))

    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const list = await read($, sessions)
    const files = [...(await read($, handoffs))].sort((a, b) => a.secs - b.secs)
    const stamp = await read($, scannedAt)
    const flipped = new Set(await read($, toggled))
    const isSectionOpen = (s: Section) => SECTION[s].isOpenByDefault !== flipped.has(`sec:${s}`)
    const isRowOpen = (id: string) => flipped.has(`row:${id}`)

    const CallLine = (call: Call, indent: number, color: string) => (
      <Box paddingLeft={indent}>
        <Text wrap="truncate-end">
          <Text color={color}>{`${call.tool} `}</Text>
          <Text color="text">{call.text}</Text>
        </Text>
      </Box>
    )

    // One line: what it is on the left, context and age on the right.
    const Line = (left: RenderChildren, right: string, rightColor = 'inactive', indent = 0) => (
      <Box justifyContent="space-between" paddingLeft={indent}>
        <Box flexShrink={1}>{left}</Box>
        <Box flexShrink={0} paddingLeft={1}>
          <Text color={rightColor}>{right}</Text>
        </Box>
      </Box>
    )

    const SubLine = (x: Sub, isDetailed: boolean) => (
      <Box flexDirection="column">
        {Line(
          <Text wrap="truncate-end">
            <Text color={x.state === 'waiting' ? 'warning' : 'inactive'}>{'↳ '}</Text>
            <Text color="ide">{'SUB '}</Text>
            <Text color="text">{x.name}</Text>
            <Text color="inactive">{` ${x.model || x.type}`}</Text>
          </Text>,
          age(x.secs),
          'inactive',
          4,
        )}
        {(isDetailed || x.state === 'waiting') && x.pending && CallLine(x.pending, 8, 'warning')}
      </Box>
    )

    const SessionBlock = (s: Session, g: Group) => {
      const sec = SECTION[g]
      const isLoud = g === 'question' || g === 'permission'
      const isDetailed = isRowOpen(s.sessionId)
      const waitingSubs = s.subs.filter(x => x.state === 'waiting')
      const shownSubs = isDetailed ? s.subs : waitingSubs
      const headline = s.pending.at(-1)
      const ctx = s.ctx > 0 ? `${s.ctxPct}% ` : ''
      const isStuck = isLoud && !headline && waitingSubs.length === 0 && (s.turnSecs ?? 0) > QUIET_S
      const note = isStuck
        ? `says waiting, but no open call and no turn for ${age(s.turnSecs ?? 0)}: check the chat`
        : isLoud && !headline
          ? waitingSubs.length > 0
            ? ''
            : s.last || 'no open call in transcript'
          : g === 'finished'
            ? s.last
            : ''

      return (
        <Box flexDirection="column">
          {Line(
            <Button key={`row:${s.sessionId}`} plain onPress={noop}>
              <Text wrap="truncate-end">
                <Text color="inactive">{isDetailed ? '▾ ' : '▸ '}</Text>
                <Text color={s.kind === 'bg' ? 'suggestion' : 'claude'}>{`${kindTag(s.kind)} `}</Text>
                <Text color="text" bold={isLoud}>{s.name}</Text>
                {s.tab && <Text color="inactive">{` (${s.tab})`}</Text>}
                <Text color="inactive">{s.subs.length > 0 ? ` +${s.subs.length}` : ''}</Text>
              </Text>
            </Button>,
            `${ctx}${age(s.secs)}`,
            BAND_COLOR[s.ctxBand] ?? 'error',
          )}
          {isLoud && headline && CallLine(headline, 7, sec.color)}
          {headline?.options && headline.options.length > 0 && (
            <Box paddingLeft={7}>
              <Text color="inactive" wrap="truncate-end">{headline.options.join('  /  ')}</Text>
            </Box>
          )}
          {note && (
            <Box paddingLeft={7}>
              <Text color={isStuck ? 'warning' : 'inactive'} wrap="truncate-end">{note}</Text>
            </Box>
          )}
          {s.ctxBand >= 3 && (
            <Box paddingLeft={7}>
              <Text color="error">{`context ${s.ctxPct}%: /compact or hand off`}</Text>
            </Box>
          )}
          {isDetailed && (
            <Box flexDirection="column" paddingLeft={7}>
              {s.branch && <Text color="inactive">{`branch ${s.branch}`}</Text>}
              {s.pending.slice(0, -1).map(c => CallLine(c, 0, sec.color))}
              {s.last && g !== 'finished' && <Text color="inactive" wrap="truncate-end">{`last ${s.last}`}</Text>}
            </Box>
          )}
          {shownSubs.map(x => SubLine(x, isDetailed))}
        </Box>
      )
    }

    const HandoffLine = (f: Handoff) =>
      Line(
        <Text wrap="truncate-end">
          <Text color="text">{f.file}</Text>
          <Text color="inactive">{` ${f.owner}`}</Text>
        </Text>,
        age(f.secs),
        'inactive',
        2,
      )

    const SectionBlock = (key: Section, count: number, body: () => RenderChildren) => {
      const sec = SECTION[key]
      const isSecOpen = isSectionOpen(key)

      return (
        <Box flexDirection="column" marginTop={1}>
          <Box>
            <Button key={`sec:${key}`} plain onPress={noop}>
              <Text>
                <Text color={sec.color} bold>{`${isSecOpen ? '▾' : '▸'} ${sec.title}`}</Text>
                <Text color="inactive">{` ${count}`}</Text>
              </Text>
            </Button>
            {/* The rule fills what the title leaves: one clipped line, so it never wraps. */}
            <Box flexGrow={1} height={1} overflow="hidden" marginLeft={1}>
              <Text color="promptBorder">{RULE}</Text>
            </Box>
          </Box>
          {isSecOpen && body()}
        </Box>
      )
    }

    const groups = (['question', 'permission', 'finished', 'working'] as const)
      .map(g => ({ g, rows: list.filter(s => s.group === g) }))
      .filter(({ rows }) => rows.length > 0)
    const repeated = repeats(list)
    const RepeatLine = ([key, who]: [string, string[]]) =>
      Line(
        <Text wrap="truncate-end">
          <Text color="warning">{`${key} `}</Text>
          <Text color="text">{`×${who.length}`}</Text>
          <Text color="inactive">{`  ${who.join(', ')}`}</Text>
        </Text>,
        '',
        'inactive',
        2,
      )
    const now = await $.clock.now()
    const ago = stamp === 0 ? 'scanning' : `updated ${age(Math.max(0, Math.round((now - stamp) / 1000)))} ago`

    return (
      <Box flexDirection="column" paddingX={1}>
        {groups
          .filter(({ g }) => g === 'question' || g === 'permission')
          .map(({ g, rows }) => SectionBlock(g, rows.length, () => rows.map(s => SessionBlock(s, g))))}
        {repeated.length > 0 && SectionBlock('repeats', repeated.length, () => repeated.map(RepeatLine))}
        {groups
          .filter(({ g }) => g === 'finished' || g === 'working')
          .map(({ g, rows }) => SectionBlock(g, rows.length, () => rows.map(s => SessionBlock(s, g))))}
        {files.length > 0 && SectionBlock('handoffs', files.length, () => files.map(HandoffLine))}
        <Box justifyContent="space-between" marginTop={1}>
          <Text color="inactive">{`live · ${ago} · ${list.length} chats`}</Text>
          <Button key="refresh" hotkey="r" plain onPress={noop}>
            refresh
          </Button>
        </Box>
      </Box>
    )
  })
}
