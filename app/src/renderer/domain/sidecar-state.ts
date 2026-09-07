// Pure state and transition rules for the sidecar lifecycle. No imports:
// this is the one place the shape of "what the engine is doing" lives.

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

// starting: a fresh spawn or a retry can succeed, crash again or give up.
// ready: healthy until it dies.
// crashed: mid backoff, waiting to retry or about to give up.
// failed: terminal until a manual restart begins a new "starting".
const ALLOWED_NEXT: Record<SidecarStatus, readonly SidecarStatus[]> = {
  starting: ['starting', 'ready', 'crashed', 'failed'],
  ready: ['ready', 'crashed', 'failed'],
  crashed: ['crashed', 'starting', 'failed'],
  failed: ['failed', 'starting'],
}

/** Adopts `next` when it is a legal transition from `state`, otherwise holds. */
export function sidecarStateReducer(state: SidecarState, next: SidecarState): SidecarState {
  return ALLOWED_NEXT[state.status].includes(next.status) ? next : state
}
