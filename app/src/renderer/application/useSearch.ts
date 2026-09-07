import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { asSearchError, initialSearchState, searchStateReducer, type SearchState } from '../domain/search-state'
import type { SearchPort } from './ports'

export interface UseSearch {
  state: SearchState
  query: string
  setQuery: (query: string) => void
}

/**
 * Runs a search per keystroke and abandons the one before it.
 *
 * There is no debounce. Stage 1 is a local full-text lookup measured in
 * milliseconds, so waiting to see whether the user types another character
 * would add more delay than the search costs. The abort is what keeps that
 * safe: at most one request is ever in flight.
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

    return () => controller.abort()
  }, [query, port])

  return { state, query, setQuery: useCallback((next: string) => setQuery(next), []) }
}
