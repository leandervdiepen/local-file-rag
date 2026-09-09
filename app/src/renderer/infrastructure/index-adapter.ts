import type { FilePage, IndexPort } from '../application/ports'
import type { IndexProgress, IndexStats } from '../domain/indexing'
import type { IndexedFileRow } from '../domain/skip-reasons'
import type { FileKind } from '../domain/search-results'
import type { SidecarClient } from './sidecar-client'

interface WireProgress {
  folder_id: string
  files_seen: number
  files_indexed: number
  files_skipped: number
  pages_indexed: number
  pages_embedded: number
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
    pagesEmbedded: wire.pages_embedded,
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

interface WireFile {
  id: string
  path: string
  kind: string
  state: string
  skip_reason: string | null
  size_bytes: number
  page_count: number
  truncated_pages: boolean
}

const KINDS: readonly string[] = ['pdf', 'image', 'text']

function toFile(wire: WireFile): IndexedFileRow {
  return {
    id: wire.id,
    path: wire.path,
    kind: (KINDS.includes(wire.kind) ? wire.kind : 'unknown') as FileKind,
    state: wire.state === 'skipped' ? 'skipped' : 'text_indexed',
    skipReason: wire.skip_reason,
    sizeBytes: wire.size_bytes,
    pageCount: wire.page_count,
    truncatedPages: wire.truncated_pages,
  }
}

export function createIndexPort(client: SidecarClient): IndexPort {
  return {
    async files(state, cursor): Promise<FilePage> {
      const query = new URLSearchParams({ state, ...(cursor ? { cursor } : {}) })
      const body = await client.json<{ files: WireFile[]; next_cursor: string | null }>(`/index/files?${query}`)
      return { files: body.files.map(toFile), nextCursor: body.next_cursor }
    },

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
