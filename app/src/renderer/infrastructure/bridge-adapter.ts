import type { Bridge } from '../../preload/bridge-types'
import type { NativeActionsPort, SecretsPort, SidecarPort } from '../application/ports'

declare global {
  interface Window {
    bridge: Bridge
  }
}

export function createSidecarPort(bridge: Bridge = window.bridge): SidecarPort {
  return {
    getConnectionInfo: () => bridge.sidecar,
    subscribe: (onState) => bridge.onSidecarState(onState),
    restart: () => bridge.restartSidecar(),
  }
}

export function createNativeActionsPort(bridge: Bridge = window.bridge): NativeActionsPort {
  return {
    openPath: (path) => bridge.openPath(path),
    revealInFinder: (path) => bridge.revealInFinder(path),
    copyPath: (path) => bridge.copyPath(path),
    pickFolder: () => bridge.pickFolder(),
  }
}

export function createSecretsPort(bridge: Bridge = window.bridge): SecretsPort {
  return {
    setAnthropicKey: (key) => bridge.setAnthropicKey(key),
    hasAnthropicKey: () => bridge.hasAnthropicKey(),
  }
}
