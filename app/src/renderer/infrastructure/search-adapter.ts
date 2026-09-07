import type { SearchHandlers, SearchPort } from '../application/ports'
import type { FileKind, PageHit } from '../domain/search-results'
import type { SidecarClient } from './sidecar-client'

interface WireHit {
  page_id: string
  file_id: string
  path: string
  page_no: number
  kind: string
  score: number
  stage: string
  snippet: string
}

const KINDS: readonly string[] = ['pdf', 'image', 'text']

function toHit(wire: WireHit): PageHit {
  return {
    pageId: wire.page_id,
    fileId: wire.file_id,
    path: wire.path,
    pageNo: wire.page_no,
    kind: (KINDS.includes(wire.kind) ? wire.kind : 'unknown') as FileKind,
    score: wire.score,
    stage: wire.stage,
    snippet: wire.snippet,
  }
}

export function createSearchPort(client: SidecarClient): SearchPort {
  return {
    search(query, handlers: SearchHandlers, signal) {
      const path = `/search?q=${encodeURIComponent(query)}`
      return client.stream(
        path,
        (name, payload) => {
          if (name === 'candidates') {
            const body = payload as { hits: WireHit[]; took_ms: number }
            handlers.onCandidates(body.hits.map(toHit), body.took_ms)
          } else if (name === 'done') {
            handlers.onFinished()
          }
        },
        signal,
      )
    },
  }
}
