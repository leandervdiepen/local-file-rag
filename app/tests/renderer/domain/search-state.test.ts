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

  it('enters the partial state the moment candidates land', () => {
    const partial = searchStateReducer(started(), { type: 'candidates', queryId: '1', hits, tookMs: 8 })

    expect(partial.phase).toBe('reading')
    expect(partial.hits).toEqual(hits)
    expect(partial.tookMs).toBe(8)
  })

  it('tracks how far the vision model has read', () => {
    const partial = searchStateReducer(started(), { type: 'candidates', queryId: '1', hits, tookMs: 8 })
    const reading = searchStateReducer(partial, { type: 'progress', queryId: '1', pagesRead: 3, pagesTotal: 12 })

    expect(reading.reading).toEqual({ pagesRead: 3, pagesTotal: 12 })
    expect(reading.hits).toEqual(hits)
  })

  it('replaces the candidates with the reranked results and clears the progress on done', () => {
    const reranked: PageHit[] = [{ ...hits[0]!, pageId: 'b:2', fileId: 'b', score: 9, stage: 'visual' }]
    const partial = searchStateReducer(started(), { type: 'candidates', queryId: '1', hits, tookMs: 8 })
    const reading = searchStateReducer(partial, { type: 'progress', queryId: '1', pagesRead: 1, pagesTotal: 1 })
    const results = searchStateReducer(reading, { type: 'results', queryId: '1', hits: reranked, tookMs: 4200 })
    const done = searchStateReducer(results, { type: 'finished', queryId: '1' })

    expect(done.phase).toBe('done')
    expect(done.hits).toEqual(reranked)
    expect(done.reading).toBeNull()
  })

  it('keeps reporting the time the user waited for results, not the time reranking took', () => {
    const reranked: PageHit[] = [{ ...hits[0]!, pageId: 'b:2', stage: 'visual' }]
    const partial = searchStateReducer(started(), { type: 'candidates', queryId: '1', hits, tookMs: 31 })
    const results = searchStateReducer(partial, { type: 'results', queryId: '1', hits: reranked, tookMs: 4200 })

    expect(results.tookMs).toBe(31)
  })

  it('ignores progress from a search the user has moved past', () => {
    const current = started('invoices', '2')
    const stale = searchStateReducer(current, { type: 'progress', queryId: '1', pagesRead: 1, pagesTotal: 5 })

    expect(stale.reading).toBeNull()
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
