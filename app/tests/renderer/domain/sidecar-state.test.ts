import { describe, expect, it } from 'vitest'
import { initialSidecarState, sidecarStateReducer, type SidecarState } from '../../../src/renderer/domain/sidecar-state'

const starting: SidecarState = { status: 'starting' }
const ready: SidecarState = { status: 'ready', baseUrl: 'http://127.0.0.1:5173' }
const crashed: SidecarState = { status: 'crashed', reason: 'exited', attempt: 1, maxAttempts: 3 }
const failed: SidecarState = { status: 'failed', reason: 'gave up' }

describe('sidecarStateReducer', () => {
  it('starts in starting', () => {
    expect(initialSidecarState).toEqual(starting)
  })

  it.each([
    { from: starting, to: ready },
    { from: starting, to: crashed },
    { from: starting, to: failed },
    { from: ready, to: crashed },
    { from: ready, to: failed },
    { from: crashed, to: starting },
    { from: crashed, to: failed },
    { from: failed, to: starting },
  ])('allows $from.status -> $to.status', ({ from, to }) => {
    expect(sidecarStateReducer(from, to)).toEqual(to)
  })

  it.each([
    { from: ready, to: starting },
    { from: crashed, to: ready },
    { from: failed, to: ready },
    { from: failed, to: crashed },
  ])('ignores the illegal transition $from.status -> $to.status and holds', ({ from, to }) => {
    expect(sidecarStateReducer(from, to)).toEqual(from)
  })

  it('accepts a same-status update as a refresh, not a rejection', () => {
    const nextReady: SidecarState = { status: 'ready', baseUrl: 'http://127.0.0.1:6000' }
    expect(sidecarStateReducer(ready, nextReady)).toEqual(nextReady)
  })
})
