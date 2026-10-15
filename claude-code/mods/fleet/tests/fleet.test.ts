import { expect, mock, test } from 'claude-code/testing'

const FILES: Record<string, object> = {
  '1.json': { pid: 1, sessionId: 'a', name: 'worker-busy', status: 'busy', updatedAt: 0 },
  '2.json': { pid: 2, sessionId: 'b', name: 'worker-perm', status: 'waiting', waitingFor: 'permission prompt', statusUpdatedAt: 0 },
  '3.json': { pid: 3, sessionId: 'c', name: 'worker-ask', status: 'waiting', waitingFor: 'input needed', statusUpdatedAt: 0 },
  '4.json': { pid: 4, sessionId: 'd', name: 'dead-one', status: 'waiting', waitingFor: 'input needed', statusUpdatedAt: 0 },
}

test('counts only live sessions waiting on the person', async ($, on) => {
  mock.env(on, { HOME: '/h' })
  const statuses: (string | undefined)[] = []
  on('session.start', async (_$, e) => e as never)
  on('command.register', async () => ({ value: undefined }) as never)
  on('session.id', async () => ({ value: 'self' }) as never)
  on('clock.now', async () => ({ value: 120000 }) as never)
  on('clock.every', async () => ({ value: undefined }) as never)
  on('fs.list', async () => ({ value: Object.keys(FILES).map(name => ({ name, kind: 'file', size: 1, mtimeMs: 0, isLink: false })) }) as never)
  on('fs.read', async (_$, e) => ({ value: JSON.stringify(FILES[e.path.split('/').pop()!]) }) as never)
  // pid 4 has exited: ps does not list it
  on('process.run', async () => ({ value: { exitCode: 0, stdout: '1\n2\n3\n', stderr: '' } }) as never)
  on('ui.status', async (_$, e) => {
    statuses.push(e.text)
    return { value: undefined } as never
  })

  await $.session.start({ cwd: '/h', surface: 'terminal', isInteractive: true })

  expect(statuses.at(-1)).toBe('fleet: 1 question · 1 permission')
})
