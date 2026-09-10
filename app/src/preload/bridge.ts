import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'
import type { Bridge, SidecarStateEvent } from './bridge-types'
import { IPC_CHANNELS } from './ipc-channels'

function readAdditionalArgument(flag: string): string {
  const prefix = `--${flag}=`
  const found = process.argv.find((arg) => arg.startsWith(prefix))
  return found ? found.slice(prefix.length) : ''
}

const bridge: Bridge = {
  sidecar: {
    // The real port is only known once the sidecar handshake completes,
    // so this is a best-effort initial value. onSidecarState carries the
    // authoritative baseUrl for the current connection, restarts included.
    baseUrl: readAdditionalArgument('sidecar-base-url'),
    token: readAdditionalArgument('sidecar-token'),
  },
  openPath: (path) => ipcRenderer.invoke(IPC_CHANNELS.openPath, path),
  revealInFinder: (path) => ipcRenderer.invoke(IPC_CHANNELS.revealInFinder, path),
  copyPath: (path) => ipcRenderer.invoke(IPC_CHANNELS.copyPath, path),
  pickFolder: () => ipcRenderer.invoke(IPC_CHANNELS.pickFolder),
  setProviderKey: (provider, key) => ipcRenderer.invoke(IPC_CHANNELS.setProviderKey, provider, key),
  providersWithKeys: () => ipcRenderer.invoke(IPC_CHANNELS.providersWithKeys),
  restartSidecar: () => ipcRenderer.invoke(IPC_CHANNELS.restartSidecar),
  onWindowShown: (listener) => {
    const handler = (): void => listener()
    ipcRenderer.on(IPC_CHANNELS.windowShown, handler)
    return () => ipcRenderer.removeListener(IPC_CHANNELS.windowShown, handler)
  },

  onSidecarState: (listener) => {
    // The sidecar can reach ready before this listener attaches, and main
    // only pushes on change, so a plain subscription can miss it. Attach the
    // live listener first, then fetch a catch-up snapshot; if a live push
    // already landed while that fetch was in flight, the (now stale)
    // snapshot is dropped instead of overwriting newer state.
    let receivedLiveUpdate = false

    const handler = (_event: IpcRendererEvent, state: SidecarStateEvent): void => {
      receivedLiveUpdate = true
      listener(state)
    }
    ipcRenderer.on(IPC_CHANNELS.sidecarState, handler)

    void ipcRenderer.invoke(IPC_CHANNELS.getSidecarState).then((state: SidecarStateEvent) => {
      if (!receivedLiveUpdate) listener(state)
    })

    return () => ipcRenderer.removeListener(IPC_CHANNELS.sidecarState, handler)
  },
}

contextBridge.exposeInMainWorld('bridge', bridge)
