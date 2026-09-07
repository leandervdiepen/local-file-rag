import { app, BrowserWindow, ipcMain } from 'electron'
import { randomBytes } from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createMainWindow } from './window'
import { resolveSidecarCommand } from './sidecar-command'
import { createSidecarProcess, SidecarProcess } from './sidecar-process'
import { createNativeActions, pickFolder } from './native-actions'
import { createIndexedFolders } from './indexed-folders'
import { setAnthropicKey, hasAnthropicKey } from './secrets'
import { IPC_CHANNELS } from '../preload/ipc-channels'
import type { SidecarStateEvent } from '../preload/bridge-types'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const preloadPath = path.join(__dirname, '../preload/bridge.js')
// Dev layout: app/out/main -> app/out -> app -> repo root -> sidecar.
const sidecarProjectPath = path.join(__dirname, '../../../sidecar')

let sidecarProcess: SidecarProcess | null = null
let mainWindow: BrowserWindow | null = null

function startSidecar(token: string): SidecarProcess {
  const { command, args } = resolveSidecarCommand({
    isPackaged: app.isPackaged,
    resourcesPath: process.resourcesPath,
    sidecarProjectPath,
    port: 0,
    token,
  })

  const process_ = createSidecarProcess({
    command,
    args,
    onLog: (line) => console.log(`[sidecar] ${line}`),
  })
  process_.onState((state: SidecarStateEvent) => {
    mainWindow?.webContents.send(IPC_CHANNELS.sidecarState, state)
  })
  process_.start()
  return process_
}

function readyBaseUrl(): string | null {
  const state = sidecarProcess?.getState()
  return state?.status === 'ready' ? state.baseUrl : null
}

function registerIpcHandlers(getWindow: () => BrowserWindow | null, token: string): void {
  const native = createNativeActions(createIndexedFolders(token, readyBaseUrl))

  ipcMain.handle(IPC_CHANNELS.openPath, (_event, targetPath: string) => native.openPath(targetPath))
  ipcMain.handle(IPC_CHANNELS.revealInFinder, (_event, targetPath: string) => native.revealInFinder(targetPath))
  ipcMain.handle(IPC_CHANNELS.copyPath, (_event, targetPath: string) => native.copyPath(targetPath))
  ipcMain.handle(IPC_CHANNELS.pickFolder, () => {
    const window = getWindow()
    return window ? pickFolder(window) : null
  })
  ipcMain.handle(IPC_CHANNELS.setAnthropicKey, (_event, key: string) => setAnthropicKey(key))
  ipcMain.handle(IPC_CHANNELS.hasAnthropicKey, () => hasAnthropicKey())
  ipcMain.handle(IPC_CHANNELS.restartSidecar, () => sidecarProcess?.restart())
  ipcMain.handle(IPC_CHANNELS.getSidecarState, (): SidecarStateEvent => sidecarProcess?.getState() ?? { status: 'starting' })
}

app.whenReady().then(() => {
  const token = randomBytes(32).toString('hex')
  sidecarProcess = startSidecar(token)
  mainWindow = createMainWindow({ preloadPath, sidecarToken: token })
  registerIpcHandlers(() => mainWindow, token)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow({ preloadPath, sidecarToken: token })
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', (event) => {
  if (!sidecarProcess) return
  event.preventDefault()
  const toStop = sidecarProcess
  sidecarProcess = null
  void toStop.stop().then(() => app.quit())
})
