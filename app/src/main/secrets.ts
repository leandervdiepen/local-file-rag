import { app, safeStorage } from 'electron'
import { promises as fs } from 'node:fs'
import path from 'node:path'

/**
 * Provider API keys, encrypted at rest by the OS keychain (D17, D41).
 *
 * The renderer can put a key here and can ask which providers have one. It can
 * never read one back: decryption is main-only, and the plaintext goes
 * straight to the sidecar over the authenticated loopback API, which holds it
 * in memory for the life of the process and never writes it down.
 */

// Anything else is a path segment someone chose, and this builds a filename.
const PROVIDER = /^[a-z][a-z0-9-]{0,30}$/

function keyDirectory(): string {
  return path.join(app.getPath('userData'), 'provider-keys')
}

function keyFilePath(provider: string): string {
  if (!PROVIDER.test(provider)) throw new Error(`${provider} is not a provider id.`)
  return path.join(keyDirectory(), `${provider}.enc`)
}

export async function setProviderKey(provider: string, key: string): Promise<void> {
  const file = keyFilePath(provider)
  if (!key.trim()) {
    await fs.rm(file, { force: true })
    return
  }
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('This Mac will not encrypt the key, so it has not been saved.')
  }
  await fs.mkdir(keyDirectory(), { recursive: true })
  await fs.writeFile(file, safeStorage.encryptString(key.trim()), { mode: 0o600 })
}

export async function providersWithKeys(): Promise<string[]> {
  try {
    const files = await fs.readdir(keyDirectory())
    return files.filter((name) => name.endsWith('.enc')).map((name) => name.slice(0, -'.enc'.length))
  } catch {
    return []
  }
}

/** Main-only. The plaintext leaves this process only to reach the sidecar. */
export async function decryptProviderKey(provider: string): Promise<string | null> {
  try {
    return safeStorage.decryptString(await fs.readFile(keyFilePath(provider)))
  } catch {
    return null
  }
}
