import type { SidecarState } from '../../src/renderer/domain/sidecar-state'
import type { SidecarPort } from '../../src/renderer/application/ports'

export interface FakeSidecarPort extends SidecarPort {
  emit: (state: SidecarState) => void
  readonly restartCalls: number
}

/** A real, working in-memory SidecarPort, not a mock with call expectations. */
export function createFakeSidecarPort(): FakeSidecarPort {
  const listeners = new Set<(state: SidecarState) => void>()
  let restartCalls = 0

  return {
    getConnectionInfo: () => ({ baseUrl: 'http://127.0.0.1:0', token: 'fake-token' }),
    subscribe: (onState) => {
      listeners.add(onState)
      return () => listeners.delete(onState)
    },
    restart: async () => {
      restartCalls += 1
    },
    emit: (state) => {
      for (const listener of listeners) listener(state)
    },
    get restartCalls() {
      return restartCalls
    },
  }
}
