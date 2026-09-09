import type { FoldersPort } from '../application/ports'
import type { IndexedFolder } from '../domain/indexing'
import type { SidecarClient } from './sidecar-client'

interface WireFolder {
  id: string
  path: string
  enabled: boolean
  added_at: string
}

function toFolder(wire: WireFolder): IndexedFolder {
  return { id: wire.id, path: wire.path, enabled: wire.enabled, addedAt: wire.added_at }
}

export function createFoldersPort(client: SidecarClient): FoldersPort {
  return {
    async list() {
      const body = await client.json<{ folders: WireFolder[] }>('/folders')
      return body.folders.map(toFolder)
    },

    async add(path) {
      return toFolder(await client.json<WireFolder>('/folders', {
        method: 'POST',
        body: JSON.stringify({ path }),
        headers: { 'Content-Type': 'application/json' },
      }))
    },

    async remove(id) {
      await client.send(`/folders/${encodeURIComponent(id)}`, 'DELETE')
    },

    async setEnabled(id, enabled) {
      return toFolder(
        await client.json<WireFolder>(`/folders/${encodeURIComponent(id)}`, {
          method: 'PATCH',
          body: JSON.stringify({ enabled }),
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    },
  }
}
