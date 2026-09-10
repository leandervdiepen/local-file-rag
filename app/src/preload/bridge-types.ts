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
  setProviderKey: (provider: string, key: string) => Promise<void>
  providersWithKeys: () => Promise<string[]>
  /** The window was brought to the front by the global shortcut. */
  onWindowShown: (listener: () => void) => () => void
  onSidecarState: (listener: (state: SidecarStateEvent) => void) => () => void
  restartSidecar: () => Promise<void>
}
