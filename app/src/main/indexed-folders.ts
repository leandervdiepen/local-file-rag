interface WireFolders {
  folders: { path: string; enabled: boolean }[]
}

/**
 * The folders the sidecar is actually indexing, asked of the sidecar directly.
 *
 * Main does not take this list from the renderer. The allowlist is what stops
 * a renderer bug from turning `shell.openPath` into a way to open any file on
 * the machine, and a list the renderer supplies would be a guard asking its
 * attacker what to allow.
 *
 * Read on every check rather than cached. It is a loopback request for a
 * handful of rows, and a cache would mean a folder added a second ago cannot
 * be opened yet. Anything that goes wrong returns no roots, so the failure is
 * a path that will not open rather than one that opens when it should not.
 */
export function createIndexedFolders(token: string, baseUrl: () => string | null) {
  return async function allowedRoots(): Promise<string[]> {
    const url = baseUrl()
    if (!url) return []

    try {
      const response = await fetch(`${url}/folders`, { headers: { Authorization: `Bearer ${token}` } })
      if (!response.ok) return []
      const body = (await response.json()) as WireFolders
      return body.folders.filter((folder) => folder.enabled).map((folder) => folder.path)
    } catch {
      return []
    }
  }
}

export type AllowedRoots = ReturnType<typeof createIndexedFolders>
