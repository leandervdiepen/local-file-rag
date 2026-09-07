import type { PageHit } from './search-results'

/**
 * `searching` is the moment before stage 1 answers. `reading` is the partial
 * state: stage 1 candidates are on screen while the vision model reads the
 * pages it has not seen, and it is the state the user judges the app by.
 */
export type SearchPhase = 'idle' | 'searching' | 'reading' | 'done' | 'error'

export interface ReadingProgress {
  pagesRead: number
  pagesTotal: number
}

export interface SearchError {
  code: string
  message: string
}

export interface SearchState {
  phase: SearchPhase
  queryId: string
  query: string
  hits: PageHit[]
  tookMs: number | null
  reading: ReadingProgress | null
  error: SearchError | null
}

export const initialSearchState: SearchState = {
  phase: 'idle',
  queryId: '',
  query: '',
  hits: [],
  tookMs: null,
  reading: null,
  error: null,
}

export type SearchEvent =
  | { type: 'started'; queryId: string; query: string }
  | { type: 'candidates'; queryId: string; hits: PageHit[]; tookMs: number }
  | { type: 'progress'; queryId: string; pagesRead: number; pagesTotal: number }
  | { type: 'results'; queryId: string; hits: PageHit[]; tookMs: number }
  | { type: 'finished'; queryId: string }
  | { type: 'failed'; queryId: string; error: SearchError }
  | { type: 'cleared' }

/**
 * Drives one search from keystroke to results.
 *
 * Every event carries the id of the search that produced it and anything from
 * an older one is dropped. A user typing fast outruns the network, and a
 * response landing after a newer one would silently show results for a query
 * that is no longer in the box.
 *
 * A new search keeps the previous hits on screen until its own arrive.
 * Blanking the list on each keystroke makes a search that takes ten
 * milliseconds look like one that failed and recovered.
 */
export function searchStateReducer(state: SearchState, event: SearchEvent): SearchState {
  if (event.type === 'cleared') return initialSearchState
  if (event.type === 'started') {
    return { ...state, phase: 'searching', queryId: event.queryId, query: event.query, reading: null, error: null }
  }
  if (event.queryId !== state.queryId) return state

  switch (event.type) {
    case 'candidates':
      return { ...state, phase: 'reading', hits: event.hits, tookMs: event.tookMs }
    case 'progress':
      return { ...state, reading: { pagesRead: event.pagesRead, pagesTotal: event.pagesTotal } }
    case 'results':
      return { ...state, hits: event.hits, tookMs: event.tookMs }
    case 'finished':
      return { ...state, phase: 'done', reading: null }
    case 'failed':
      return { ...state, phase: 'error', hits: [], tookMs: null, reading: null, error: event.error }
  }
}

/**
 * Narrows an unknown rejection to something the UI can display.
 *
 * Anything that is not already a coded error is reported as one rather than
 * dropped, because a search that silently stops is the failure a user cannot
 * report.
 */
export function asSearchError(value: unknown): SearchError {
  const candidate = value as Partial<SearchError> | null
  if (candidate && typeof candidate.code === 'string' && typeof candidate.message === 'string') {
    return { code: candidate.code, message: candidate.message }
  }
  return { code: 'unexpected_error', message: 'Something went wrong on this device.' }
}
