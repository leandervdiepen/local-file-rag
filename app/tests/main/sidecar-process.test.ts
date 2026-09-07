import { randomUUID } from 'node:crypto'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { afterEach, describe, expect, it } from 'vitest'
import { createSidecarProcess, type SidecarProcess } from '../../src/main/sidecar-process'
import type { SidecarStateEvent } from '../../src/preload/bridge-types'

const fixturePath = fileURLToPath(new URL('../fixtures/fake-sidecar.mjs', import.meta.url))

function spawnFake(env: NodeJS.ProcessEnv = {}, overrides: Partial<Parameters<typeof createSidecarProcess>[0]> = {}) {
  return createSidecarProcess({
    command: process.execPath,
    args: [fixturePath, '--port', '0', '--token', 'test-token'],
    env: { ...process.env, ...env },
    handshakeTimeoutMs: 2000,
    maxRestarts: 2,
    backoffMs: () => 20,
    ...overrides,
  })
}

function waitForStatus(sidecar: SidecarProcess, status: SidecarStateEvent['status']): Promise<SidecarStateEvent> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`timed out waiting for status "${status}"`)), 5000)
    if (sidecar.getState().status === status) {
      clearTimeout(timer)
      resolve(sidecar.getState())
      return
    }
    const unsubscribe = sidecar.onState((event) => {
      if (event.status === status) {
        clearTimeout(timer)
        unsubscribe()
        resolve(event)
      }
    })
  })
}

describe('sidecar-process', () => {
  const active: SidecarProcess[] = []

  afterEach(async () => {
    await Promise.all(active.splice(0).map((sidecar) => sidecar.stop()))
  })

  it('reaches ready and serves an authenticated /health', async () => {
    const sidecar = spawnFake()
    active.push(sidecar)
    sidecar.start()

    const ready = await waitForStatus(sidecar, 'ready')
    expect(ready.status).toBe('ready')
    if (ready.status !== 'ready') throw new Error('unreachable')

    const response = await fetch(`${ready.baseUrl}/health`, {
      headers: { authorization: 'Bearer test-token' },
    })
    expect(response.status).toBe(200)
    const body = (await response.json()) as { status: string; authorized: boolean }
    expect(body).toEqual({ status: 'ok', authorized: true })
  })

  it('detects a crash that happens after reaching ready, and recovers', async () => {
    const sidecar = spawnFake({ FAKE_SIDECAR_CRASH_AFTER_MS: '100' })
    active.push(sidecar)
    sidecar.start()

    await waitForStatus(sidecar, 'ready')

    const crashed = await waitForStatus(sidecar, 'crashed')
    expect(crashed).toMatchObject({ status: 'crashed', attempt: 1, maxAttempts: 2 })

    const ready = await waitForStatus(sidecar, 'ready')
    expect(ready.status).toBe('ready')
  })

  it('retries a transient crash and recovers', async () => {
    const marker = path.join(mkdtempSync(path.join(tmpdir(), 'fake-sidecar-')), randomUUID())
    const sidecar = spawnFake({ FAKE_SIDECAR_CRASH_ONCE_MARKER: marker })
    active.push(sidecar)
    sidecar.start()

    const crashed = await waitForStatus(sidecar, 'crashed')
    expect(crashed).toMatchObject({ status: 'crashed', attempt: 1, maxAttempts: 2 })

    const ready = await waitForStatus(sidecar, 'ready')
    expect(ready.status).toBe('ready')

    rmSync(path.dirname(marker), { recursive: true, force: true })
  })

  it('gives up after exhausting restarts and settles into failed', async () => {
    const sidecar = spawnFake({ FAKE_SIDECAR_FAIL: '1' })
    active.push(sidecar)
    sidecar.start()

    const first = await waitForStatus(sidecar, 'crashed')
    expect(first).toMatchObject({ attempt: 1, maxAttempts: 2 })

    const failed = await waitForStatus(sidecar, 'failed')
    expect(failed.status).toBe('failed')

    // An event that must not happen cannot be awaited, so this one waits on a duration.
    await new Promise((resolve) => setTimeout(resolve, 100))
    expect(sidecar.getState().status).toBe('failed')
  })

  it('sends SIGTERM then SIGKILL after the grace period on stop', async () => {
    const sidecar = spawnFake({ FAKE_SIDECAR_IGNORE_SIGTERM: '1' }, { shutdownGraceMs: 150 })
    active.push(sidecar)
    sidecar.start()
    await waitForStatus(sidecar, 'ready')

    const startedAt = Date.now()
    await sidecar.stop()
    expect(Date.now() - startedAt).toBeGreaterThanOrEqual(150)
  })
})
