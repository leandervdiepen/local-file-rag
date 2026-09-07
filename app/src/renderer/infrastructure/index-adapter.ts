import type { IndexPort } from '../application/ports'
import type { IndexProgress, IndexStats } from '../domain/indexing'
import type { SidecarClient } from './sidecar-client'

interface WireProgress {
  folder_id: string
  files_seen: number
  files_indexed: number
  files_skipped: number
  pages_indexed: number
  current_path: string
  done: boolean
}

interface WireStats {
  files_scanned: number
  files_text_indexed: number
  files_skipped: number
  pages_total: number
  pages_embedded: number
  bytes_on_disk: number
  skips_by_reason: Record<string, number>
}

function toProgress(wire: WireProgress): IndexProgress {
  return {
    folderId: wire.folder_id,
    filesSeen: wire.files_seen,
    filesIndexed: wire.files_indexed,
    filesSkipped: wire.files_skipped,
    pagesIndexed: wire.pages_indexed,
    currentPath: wire.current_path,
    done: wire.done,
  }
}

function toStats(wire: WireStats): IndexStats {
  return {
    filesScanned: wire.files_scanned,
    filesTextIndexed: wire.files_text_indexed,
    filesSkipped: wire.files_skipped,
    pagesTotal: wire.pages_total,
    pagesEmbedded: wire.pages_embedded,
    bytesOnDisk: wire.bytes_on_disk,
    skipsByReason: wire.skips_by_reason,
  }
}

export function createIndexPort(client: SidecarClient): IndexPort {
  return {
    async rescan() {
      await client.send('/index/rescan', 'POST')
    },

    async stats() {
      return toStats(await client.json<WireStats>('/index/stats'))
    },

    watchProgress(onProgress, signal) {
      return client.stream(
        '/index/progress',
        (name, payload) => {
          if (name === 'progress' || name === 'done') onProgress(toProgress(payload as WireProgress))
        },
        signal,
      )
    },
  }
}
