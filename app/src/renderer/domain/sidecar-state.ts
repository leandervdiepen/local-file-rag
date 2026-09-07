export type SidecarStatus = 'starting' | 'ready' | 'crashed' | 'failed'

export interface SidecarStarting {
  status: 'starting'
}

export interface SidecarReady {
  status: 'ready'
  baseUrl: string
}

export interface SidecarCrashed {
  status: 'crashed'
  reason: string
  attempt: number
  maxAttempts: number
}

export interface SidecarFailed {
  status: 'failed'
  reason: string
}

export type SidecarState = SidecarStarting | SidecarReady | SidecarCrashed | SidecarFailed

export const initialSidecarState: SidecarState = { status: 'starting' }

// Events arrive from another process, so a stale or out-of-order one must not
// walk the UI backwards into a spinner it already left. Only a restart returns
// a crashed or failed engine to starting.
const ALLOWED_NEXT: Record<SidecarStatus, readonly SidecarStatus[]> = {
  starting: ['starting', 'ready', 'crashed', 'failed'],
  ready: ['ready', 'crashed', 'failed'],
  crashed: ['crashed', 'starting', 'failed'],
  failed: ['failed', 'starting'],
}

export function sidecarStateReducer(state: SidecarState, next: SidecarState): SidecarState {
  return ALLOWED_NEXT[state.status].includes(next.status) ? next : state
}
