// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { SearchHandlers, SearchPort } from '../../../src/renderer/application/ports'
import { useSearch } from '../../../src/renderer/application/useSearch'

// Short enough that these tests never wait on the real settle delay, which is
// tuned for a person typing and makes an already loaded machine flaky.
const SETTLE = 5
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
  const started: string[] = []
  const aborted: string[] = []

  const port: SearchPort = {
    search(query, handlers, signal) {
      started.push(query)
      return new Promise<void>((resolve, reject) => {
        pending.set(query, { handlers, finish: resolve })
        signal.addEventListener('abort', () => {
          aborted.push(query)
          reject(new DOMException('Aborted', 'AbortError'))
        })
      })
    },
  }

  return { port, pending, started, aborted }
}

describe('useSearch', () => {
  it('stays idle until something is typed', () => {
    const { port } = createControllablePort()
    const { result } = renderHook(() => useSearch(port, SETTLE))

    expect(result.current.state.phase).toBe('idle')
  })

  it('shows the candidates of the search that is current', async () => {
    const { port, pending } = createControllablePort()
    const { result } = renderHook(() => useSearch(port, SETTLE))

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
    const { result } = renderHook(() => useSearch(port, SETTLE))

    act(() => result.current.setQuery('inv'))
    await waitFor(() => expect(pending.has('inv')).toBe(true))
    act(() => result.current.setQuery('invoice'))

    await waitFor(() => expect(aborted).toContain('inv'))
  })

  it('spends nothing on the letters of a word still being typed', async () => {
    const { port, started } = createControllablePort()
    const { result } = renderHook(() => useSearch(port, SETTLE))

    for (const prefix of ['i', 'in', 'inv', 'invo', 'invoi', 'invoic', 'invoice']) {
      act(() => result.current.setQuery(prefix))
    }

    await waitFor(() => expect(started).toEqual(['invoice']))
    // Long enough after the settle window that a queued prefix would have fired.
    await new Promise((resolve) => setTimeout(resolve, SETTLE * 20))
    expect(started).toEqual(['invoice'])
  })

  it('ignores a slow response from a search the user has moved past', async () => {
    const { port, pending } = createControllablePort()
    const { result } = renderHook(() => useSearch(port, SETTLE))

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
    const { result } = renderHook(() => useSearch(port, SETTLE))

    act(() => result.current.setQuery('invoice'))
    await waitFor(() => expect(pending.has('invoice')).toBe(true))
    act(() => result.current.setQuery('   '))

    await waitFor(() => expect(result.current.state.phase).toBe('idle'))
  })

  it('surfaces a failure as state the screen can render', async () => {
    const failing: SearchPort = { search: () => Promise.reject({ code: 'index_busy', message: 'Busy.' }) }
    const { result } = renderHook(() => useSearch(failing, SETTLE))

    act(() => result.current.setQuery('invoice'))

    await waitFor(() => expect(result.current.state.phase).toBe('error'))
    expect(result.current.state.error?.code).toBe('index_busy')
  })
})
