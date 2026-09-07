import { describe, expect, it } from 'vitest'
import type { PageHit } from '../../../src/renderer/domain/search-results'
import {
  asSearchError,
  initialSearchState,
  searchStateReducer,
  type SearchState,
} from '../../../src/renderer/domain/search-state'

const hits: PageHit[] = [
  { pageId: 'a:1', fileId: 'a', path: '/x/a.pdf', pageNo: 1, kind: 'pdf', score: 2, stage: 'content', snippet: 'hi' },
]

function started(query = 'invoice', queryId = '1'): SearchState {
  return searchStateReducer(initialSearchState, { type: 'started', queryId, query })
}

describe('searchStateReducer', () => {
  it('enters searching and remembers which search is current', () => {
    const state = started()

    expect(state.phase).toBe('searching')
    expect(state.query).toBe('invoice')
    expect(state.queryId).toBe('1')
  })

  it('keeps the previous results on screen while the next search runs', () => {
    const withHits = searchStateReducer(started(), { type: 'candidates', queryId: '1', hits, tookMs: 8 })
    const next = searchStateReducer(withHits, { type: 'started', queryId: '2', query: 'invoices' })

    expect(next.hits).toEqual(hits)
  })

  it('ignores results from a search the user has already moved on from', () => {
    const current = started('invoices', '2')
    const stale = searchStateReducer(current, { type: 'candidates', queryId: '1', hits, tookMs: 8 })

    expect(stale.hits).toEqual([])
  })

  it('ignores a stale failure, so an aborted search cannot show an error', () => {
    const current = started('invoices', '2')
    const stale = searchStateReducer(current, {
      type: 'failed',
      queryId: '1',
      error: { code: 'boom', message: 'x' },
    })

    expect(stale.phase).toBe('searching')
  })

  it('reaches done with the candidates and the time they took', () => {
    const withHits = searchStateReducer(started(), { type: 'candidates', queryId: '1', hits, tookMs: 8 })
    const done = searchStateReducer(withHits, { type: 'finished', queryId: '1' })

    expect(done.phase).toBe('done')
    expect(done.tookMs).toBe(8)
    expect(done.hits).toEqual(hits)
  })

  it('drops results when a search fails, so no stale list sits under an error', () => {
    const withHits = searchStateReducer(started(), { type: 'candidates', queryId: '1', hits, tookMs: 8 })
    const failed = searchStateReducer(withHits, {
      type: 'failed',
      queryId: '1',
      error: { code: 'sidecar_unreachable', message: 'The local engine is not responding.' },
    })

    expect(failed.phase).toBe('error')
    expect(failed.hits).toEqual([])
    expect(failed.error?.code).toBe('sidecar_unreachable')
  })

  it('returns to the empty state when the query is cleared', () => {
    const withHits = searchStateReducer(started(), { type: 'candidates', queryId: '1', hits, tookMs: 8 })

    expect(searchStateReducer(withHits, { type: 'cleared' })).toEqual(initialSearchState)
  })
})

describe('asSearchError', () => {
  it('passes a coded error through', () => {
    expect(asSearchError({ code: 'index_busy', message: 'Already indexing.' })).toEqual({
      code: 'index_busy',
      message: 'Already indexing.',
    })
  })

  it('gives anything else a code the UI can still display', () => {
    expect(asSearchError(new TypeError('undefined is not a function')).code).toBe('unexpected_error')
    expect(asSearchError(null).code).toBe('unexpected_error')
  })
})
