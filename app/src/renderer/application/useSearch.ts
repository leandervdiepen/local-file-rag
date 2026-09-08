import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { asSearchError, initialSearchState, searchStateReducer, type SearchState } from '../domain/search-state'
import type { SearchPort } from './ports'

/**
 * Long enough to collapse a burst of typing into one search, short enough that
 * a person who stops to read never waits for it. Stage 1 answers in tens of
 * milliseconds, so this is most of the delay before the first results.
 */
export const SEARCH_SETTLE_MS = 140

export interface UseSearch {
  state: SearchState
  query: string
  setQuery: (query: string) => void
}

/**
 * Runs one search once the typing settles, and abandons the one before it.
 *
 * A search is not cheap any more. Stage 1 is a local lookup measured in
 * milliseconds, but it hands its candidates to a vision model that reads
 * pages at about a second each, so a search fired per keystroke would put
 * seven searches worth of model work behind a seven letter word. The abort
 * covers the rest: at most one request is ever in flight, and dropping the
 * connection is what stops the reading.
 */
export function useSearch(port: SearchPort): UseSearch {
  const [query, setQuery] = useState('')
  const [state, dispatch] = useReducer(searchStateReducer, initialSearchState)
  const issued = useRef(0)

  useEffect(() => {
    if (!query.trim()) {
      dispatch({ type: 'cleared' })
      return
    }

    const controller = new AbortController()
    const settle = setTimeout(() => runSearch(), SEARCH_SETTLE_MS)

    function runSearch(): void {
      const queryId = String((issued.current += 1))
      dispatch({ type: 'started', queryId, query })

      port
        .search(
          query,
          {
            onCandidates: (hits, tookMs) => dispatch({ type: 'candidates', queryId, hits, tookMs }),
            onProgress: (pagesRead, pagesTotal) => dispatch({ type: 'progress', queryId, pagesRead, pagesTotal }),
            onResults: (hits, tookMs) => dispatch({ type: 'results', queryId, hits, tookMs }),
            onFinished: () => dispatch({ type: 'finished', queryId }),
          },
          controller.signal,
        )
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          dispatch({ type: 'failed', queryId, error: asSearchError(error) })
        })
    }

    return () => {
      clearTimeout(settle)
      controller.abort()
    }
  }, [query, port])

  return { state, query, setQuery: useCallback((next: string) => setQuery(next), []) }
}
