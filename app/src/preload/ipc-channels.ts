// Channel names are internal wiring between main and preload.
// They never cross into the bridge surface the renderer sees.

export const IPC_CHANNELS = {
  openPath: 'native-actions:open-path',
  revealInFinder: 'native-actions:reveal-in-finder',
  copyPath: 'native-actions:copy-path',
  pickFolder: 'native-actions:pick-folder',
  setProviderKey: 'secrets:set-provider-key',
  providersWithKeys: 'secrets:providers-with-keys',
  restartSidecar: 'sidecar:restart',
  sidecarState: 'sidecar:state',
  getSidecarState: 'sidecar:get-state',
} as const
