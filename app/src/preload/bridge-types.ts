// The one declaration of the renderer's window.bridge surface.
// Main and renderer both import this so a mismatch between what main sends
// and what the renderer expects is a typecheck failure, not a runtime bug.

export interface SidecarConnection {
  baseUrl: string
  token: string
}

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

export type SidecarStateEvent = SidecarStarting | SidecarReady | SidecarCrashed | SidecarFailed

export interface OpenPathResult {
  ok: boolean
  error?: string
}

export interface Bridge {
  sidecar: SidecarConnection
  openPath: (path: string) => Promise<OpenPathResult>
  revealInFinder: (path: string) => Promise<void>
  copyPath: (path: string) => Promise<void>
  pickFolder: () => Promise<string | null>
  setAnthropicKey: (key: string) => Promise<void>
  hasAnthropicKey: () => Promise<boolean>
  onSidecarState: (listener: (state: SidecarStateEvent) => void) => () => void
  // Not in the bridge spec's literal list: the design calls for a working
  // restart button on the crashed and failed states, and contextIsolation
  // leaves no other path from renderer to main for that action. Flagged in
  // the delivery report as a deliberate, minimal deviation.
  restartSidecar: () => Promise<void>
}
