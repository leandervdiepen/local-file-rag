import { clipboard, dialog, shell, type BrowserWindow } from 'electron'
import type { OpenPathResult } from '../preload/bridge-types'
import { isPathAllowed } from './allowed-paths'
import type { AllowedRoots } from './indexed-folders'

const OUTSIDE_INDEX = 'That file is outside the folders you chose to index.'

export function createNativeActions(allowedRoots: AllowedRoots) {
  return {
    async openPath(targetPath: string): Promise<OpenPathResult> {
      if (!isPathAllowed(targetPath, await allowedRoots())) return { ok: false, error: OUTSIDE_INDEX }
      const error = await shell.openPath(targetPath)
      return error ? { ok: false, error } : { ok: true }
    },

    async revealInFinder(targetPath: string): Promise<void> {
      if (!isPathAllowed(targetPath, await allowedRoots())) return
      shell.showItemInFolder(targetPath)
    },

    // No allowlist check: this writes a string the renderer already holds to
    // the clipboard and never touches the file it names.
    copyPath(targetPath: string): void {
      clipboard.writeText(targetPath)
    },
  }
}

export async function pickFolder(window: BrowserWindow): Promise<string | null> {
  const result = await dialog.showOpenDialog(window, { properties: ['openDirectory'] })
  if (result.canceled) return null
  return result.filePaths[0] ?? null
}
