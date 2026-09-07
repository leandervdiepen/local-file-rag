// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SearchHandlers, SearchPort } from '../../../src/renderer/application/ports'
import { useSearch } from '../../../src/renderer/application/useSearch'
import type { PageHit } from '../../../src/renderer/domain/search-results'

function hitFor(query: string): PageHit {
  return {
    pageId: `${query}:1`,
    fileId: query,
    path: `/x/${query}.pdf`,
    pageNo: 1,
    kind: 'pdf',
    score: 1,
    stage: 'content',
    snippet: query,
  }
}

/** A real search port whose streams are finished by hand, one query at a time. */
function createControllablePort() {
  const pending = new Map<string, { handlers: SearchHandlers; finish: () => void }>()
  const aborted: string[] = []

  const port: SearchPort = {
    search(query, handlers, signal) {
      return new Promise<void>((resolve, reject) => {
        pending.set(query, { handlers, finish: resolve })
        signal.addEventListener('abort', () => {
          aborted.push(query)
          reject(new DOMException('Aborted', 'AbortError'))
        })
      })
    },
  }

  return { port, pending, aborted }
}

describe('useSearch', () => {
  it('stays idle until something is typed', () => {
    const { port } = createControllablePort()
    const { result } = renderHook(() => useSearch(port))

    expect(result.current.state.phase).toBe('idle')
  })

  it('shows the candidates of the search that is current', async () => {
    const { port, pending } = createControllablePort()
    const { result } = renderHook(() => useSearch(port))

    act(() => result.current.setQuery('invoice'))
    await waitFor(() => expect(pending.has('invoice')).toBe(true))

    act(() => {
      pending.get('invoice')?.handlers.onCandidates([hitFor('invoice')], 7)
      pending.get('invoice')?.handlers.onFinished()
    })

    await waitFor(() => expect(result.current.state.phase).toBe('done'))
    expect(result.current.state.hits).toHaveLength(1)
    expect(result.current.state.tookMs).toBe(7)
  })

  it('abandons the previous search when the query changes', async () => {
    const { port, pending, aborted } = createControllablePort()
    const { result } = renderHook(() => useSearch(port))

    act(() => result.current.setQuery('inv'))
    await waitFor(() => expect(pending.has('inv')).toBe(true))
    act(() => result.current.setQuery('invoice'))

    await waitFor(() => expect(aborted).toContain('inv'))
  })

  it('ignores a slow response from a search the user has moved past', async () => {
    const { port, pending } = createControllablePort()
    const { result } = renderHook(() => useSearch(port))

    act(() => result.current.setQuery('inv'))
    await waitFor(() => expect(pending.has('inv')).toBe(true))
    const stale = pending.get('inv')

    act(() => result.current.setQuery('invoice'))
    await waitFor(() => expect(pending.has('invoice')).toBe(true))

    act(() => stale?.handlers.onCandidates([hitFor('inv')], 99))

    expect(result.current.state.hits).toEqual([])
  })

  it('returns to idle when the box is emptied', async () => {
    const { port, pending } = createControllablePort()
    const { result } = renderHook(() => useSearch(port))

    act(() => result.current.setQuery('invoice'))
    await waitFor(() => expect(pending.has('invoice')).toBe(true))
    act(() => result.current.setQuery('   '))

    await waitFor(() => expect(result.current.state.phase).toBe('idle'))
  })

  it('surfaces a failure as state the screen can render', async () => {
    const failing: SearchPort = { search: () => Promise.reject({ code: 'index_busy', message: 'Busy.' }) }
    const { result } = renderHook(() => useSearch(failing))

    act(() => result.current.setQuery('invoice'))

    await waitFor(() => expect(result.current.state.phase).toBe('error'))
    expect(result.current.state.error?.code).toBe('index_busy')
  })
})
