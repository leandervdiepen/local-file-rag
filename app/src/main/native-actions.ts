import { clipboard, dialog, shell, type BrowserWindow } from 'electron'
import type { OpenPathResult } from '../preload/bridge-types'
import { isPathAllowed } from './allowed-paths'

export async function openPath(targetPath: string): Promise<OpenPathResult> {
  if (!isPathAllowed(targetPath)) {
    return { ok: false, error: 'Path is outside the indexed folders.' }
  }
  const error = await shell.openPath(targetPath)
  return error ? { ok: false, error } : { ok: true }
}

export function revealInFinder(targetPath: string): void {
  if (!isPathAllowed(targetPath)) return
  shell.showItemInFolder(targetPath)
}

export function copyPath(targetPath: string): void {
  clipboard.writeText(targetPath)
}

export async function pickFolder(window: BrowserWindow): Promise<string | null> {
  const result = await dialog.showOpenDialog(window, { properties: ['openDirectory'] })
  if (result.canceled) return null
  return result.filePaths[0] ?? null
}
