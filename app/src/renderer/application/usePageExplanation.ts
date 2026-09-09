import { useEffect, useState } from 'react'
import type { Heatmap } from '../domain/heatmap'
import { asSearchError, type SearchError } from '../domain/search-state'
import type { HeatmapPort } from './ports'

export interface UsePageExplanation {
  heatmap: Heatmap | null
  error: SearchError | null
  loading: boolean
}

interface Explanation {
  key: string
  heatmap: Heatmap | null
  error: SearchError | null
}

/**
 * Fetches the explanation for one page under one query.
 *
 * The result carries the page and query it belongs to, and anything from a
 * different pair is ignored while rendering rather than cleared in an effect.
 * That way opening a second page never shows the first page's overlay, and
 * there is no frame in between where the state has been blanked.
 *
 * The page image is shown before this arrives and stays if it never does. The
 * overlay is why the page matched, and a page with no overlay is still the
 * page the user asked to see.
 */
export function usePageExplanation(port: HeatmapPort, pageId: string, query: string): UsePageExplanation {
  const [explained, setExplained] = useState<Explanation | null>(null)
  const key = `${pageId} ${query}`

  useEffect(() => {
    const controller = new AbortController()
    const settle = (result: Omit<Explanation, 'key'>) => {
      if (!controller.signal.aborted) setExplained({ key, ...result })
    }

    port
      .explain(pageId, query, controller.signal)
      .then((heatmap) => settle({ heatmap, error: null }))
      .catch((cause: unknown) => settle({ heatmap: null, error: asSearchError(cause) }))

    return () => controller.abort()
  }, [port, pageId, query, key])

  const current = explained?.key === key ? explained : null
  return { heatmap: current?.heatmap ?? null, error: current?.error ?? null, loading: current === null }
}
