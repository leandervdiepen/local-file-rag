import { decryptProviderKey, providersWithKeys } from './secrets'

/**
 * Hand every stored key to the sidecar, which holds them in memory only.
 *
 * Called each time the sidecar reaches ready, because a sidecar that crashed
 * and restarted has forgotten everything it was told and would otherwise
 * answer "add a key in Settings" to a user who already did.
 */
export async function sendStoredKeys(baseUrl: string, token: string): Promise<number> {
  let sent = 0
  for (const provider of await providersWithKeys()) {
    const key = await decryptProviderKey(provider)
    if (!key) continue
    try {
      const response = await fetch(`${baseUrl}/secrets/${encodeURIComponent(provider)}`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ key }),
      })
      if (response.ok) sent += 1
    } catch {
      // The sidecar is up but not answering yet, or is going down again. The
      // next ready event sends these anyway, so nothing here needs to retry.
    }
  }
  return sent
}

/**
 * Tell the sidecar to forget a provider's key, now rather than at restart.
 *
 * Deleting the file is not enough. The sidecar holds keys in memory, and
 * `sendStoredKeys` only ever sends the ones that exist, so a removed key went
 * on being used until the process ended.
 */
export async function forgetProviderKey(baseUrl: string, token: string, provider: string): Promise<void> {
  try {
    await fetch(`${baseUrl}/secrets/${encodeURIComponent(provider)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
  } catch {
    // The sidecar is down or restarting, and one that restarts is handed only
    // the keys still on disk, which no longer include this one.
  }
}
