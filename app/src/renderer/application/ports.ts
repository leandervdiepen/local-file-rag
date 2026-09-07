import type { SidecarState } from '../domain/sidecar-state'

export interface SidecarConnectionInfo {
  baseUrl: string
  token: string
}

export interface SidecarPort {
  getConnectionInfo: () => SidecarConnectionInfo
  subscribe: (onState: (state: SidecarState) => void) => () => void
  restart: () => Promise<void>
}

export interface OpenPathResult {
  ok: boolean
  error?: string
}

export interface NativeActionsPort {
  openPath: (path: string) => Promise<OpenPathResult>
  revealInFinder: (path: string) => Promise<void>
  copyPath: (path: string) => Promise<void>
  pickFolder: () => Promise<string | null>
}

export interface SecretsPort {
  setAnthropicKey: (key: string) => Promise<void>
  hasAnthropicKey: () => Promise<boolean>
}
