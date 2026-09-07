import { app, safeStorage } from 'electron'
import { promises as fs } from 'node:fs'
import path from 'node:path'

function keyFilePath(): string {
  return path.join(app.getPath('userData'), 'anthropic-key.enc')
}

export async function setAnthropicKey(key: string): Promise<void> {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('Encryption is not available on this machine.')
  }
  const encrypted = safeStorage.encryptString(key)
  await fs.writeFile(keyFilePath(), encrypted)
}

export async function hasAnthropicKey(): Promise<boolean> {
  try {
    await fs.access(keyFilePath())
    return true
  } catch {
    return false
  }
}

/**
 * Main-only. Sent once per launch to the sidecar over the authenticated
 * local API once that endpoint exists. Never crosses the preload bridge.
 */
export async function decryptAnthropicKey(): Promise<string | null> {
  if (!(await hasAnthropicKey())) return null
  const encrypted = await fs.readFile(keyFilePath())
  return safeStorage.decryptString(encrypted)
}
