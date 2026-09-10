import { app, BrowserWindow, ipcMain } from 'electron'
import { randomBytes } from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createMainWindow } from './window'
import { OPEN_SHORTCUT, registerOpenShortcut, unregisterOpenShortcut } from './global-shortcut'
import { resolveSidecarCommand } from './sidecar-command'
import { createSidecarProcess, SidecarProcess } from './sidecar-process'
import { createNativeActions, pickFolder } from './native-actions'
import { createIndexedFolders } from './indexed-folders'
import { setProviderKey, providersWithKeys } from './secrets'
import { sendStoredKeys } from './send-keys'
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
    // Set by the end to end test so it indexes a temporary folder into a
    // temporary database instead of into whatever this machine already has.
    dbPath: process.env['LOCAL_FILE_RAG_DB'],
  })

  const process_ = createSidecarProcess({
    command,
    args,
    onLog: (line) => console.log(`[sidecar] ${line}`),
  })
  process_.onState((state: SidecarStateEvent) => {
    mainWindow?.webContents.send(IPC_CHANNELS.sidecarState, state)
    // A sidecar that restarted has forgotten every key it was told, and would
    // answer "add a key in Settings" to a user who already did.
    if (state.status === 'ready') void sendStoredKeys(state.baseUrl, token)
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
  ipcMain.handle(IPC_CHANNELS.setProviderKey, async (_event, provider: string, key: string) => {
    await setProviderKey(provider, key)
    // Straight on to the sidecar, so the next question uses it without a restart.
    const baseUrl = readyBaseUrl()
    if (baseUrl) await sendStoredKeys(baseUrl, token)
  })
  ipcMain.handle(IPC_CHANNELS.providersWithKeys, () => providersWithKeys())
  ipcMain.handle(IPC_CHANNELS.restartSidecar, () => sidecarProcess?.restart())
  ipcMain.handle(IPC_CHANNELS.getSidecarState, (): SidecarStateEvent => sidecarProcess?.getState() ?? { status: 'starting' })
}

app.whenReady().then(() => {
  const token = randomBytes(32).toString('hex')
  sidecarProcess = startSidecar(token)
  mainWindow = createMainWindow({ preloadPath, sidecarToken: token })
  registerIpcHandlers(() => mainWindow, token)

  if (!registerOpenShortcut(() => mainWindow)) {
    console.log(`[main] ${OPEN_SHORTCUT} is taken by another app, opening from the Dock still works`)
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow({ preloadPath, sidecarToken: token })
    }
  })
})

app.on('will-quit', unregisterOpenShortcut)

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
