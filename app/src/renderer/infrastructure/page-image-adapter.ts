import type { PageImagePort, PageImageSize } from '../application/ports'
import type { SidecarClient } from './sidecar-client'

const DEFAULT_CAPACITY = 240

/**
 * Object URLs for rendered pages, kept in a bounded most-recently-used cache.
 *
 * A page image never changes for a page id, so a second request for one
 * already on screen must not become a second fetch: scrolling a result list
 * back up would otherwise re-download every thumbnail it passes. The promise
 * is what gets stored, so two rows asking at once share one request.
 *
 * The cache is bounded because object URLs hold their blob until revoked, and
 * a long session over a large index would otherwise keep every page it ever
 * showed. Eviction revokes, which is the only thing that frees the memory.
 */
export function createPageImagePort(client: SidecarClient, capacity: number = DEFAULT_CAPACITY): PageImagePort {
  const urls = new Map<string, Promise<string>>()

  function evictOldest(): void {
    const oldest = urls.keys().next()
    if (oldest.done) return
    const evicted = urls.get(oldest.value)
    urls.delete(oldest.value)
    void evicted?.then(URL.revokeObjectURL).catch(() => undefined)
  }

  return {
    imageUrl(pageId: string, size: PageImageSize): Promise<string> {
      const key = `${pageId}:${size}`
      const cached = urls.get(key)
      if (cached) {
        urls.delete(key)
        urls.set(key, cached)
        return cached
      }

      const pending = client
        .blob(`/pages/${encodeURIComponent(pageId)}/image?size=${size}`)
        .then(URL.createObjectURL)
        .catch((error: unknown) => {
          urls.delete(key)
          throw error
        })

      urls.set(key, pending)
      if (urls.size > capacity) evictOldest()
      return pending
    },
  }
}
