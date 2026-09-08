// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { HeatmapPort } from '../../../src/renderer/application/ports'
import { usePageExplanation } from '../../../src/renderer/application/usePageExplanation'
import type { Heatmap } from '../../../src/renderer/domain/heatmap'

function heatmapFor(pageId: string): Heatmap {
  return {
    rows: 1,
    cols: 1,
    combined: [[1]],
    threshold: 0.9,
    thresholdPercentile: 90,
    tokens: [{ token: pageId, values: [[1]] }],
  }
}

function createPort() {
  const pending = new Map<string, (heatmap: Heatmap) => void>()
  const asked: string[] = []
  const aborted: string[] = []

  const port: HeatmapPort = {
    explain(pageId, query, signal) {
      const key = `${pageId}|${query}`
      asked.push(key)
      return new Promise<Heatmap>((resolve, reject) => {
        pending.set(key, resolve)
        signal.addEventListener('abort', () => {
          aborted.push(key)
          reject(new DOMException('Aborted', 'AbortError'))
        })
      })
    },
  }
  return { port, pending, asked, aborted }
}

describe('usePageExplanation', () => {
  it('is loading until the explanation lands', async () => {
    const { port, pending } = createPort()
    const { result } = renderHook(() => usePageExplanation(port, 'a:1', 'funnel'))

    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(pending.has('a:1|funnel')).toBe(true))
    act(() => pending.get('a:1|funnel')?.(heatmapFor('a:1')))

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.heatmap?.tokens[0]?.token).toBe('a:1')
  })

  it('never shows the previous page explanation against a new page', async () => {
    const { port, pending, aborted } = createPort()
    const { result, rerender } = renderHook(({ id }) => usePageExplanation(port, id, 'funnel'), {
      initialProps: { id: 'a:1' },
    })

    await waitFor(() => expect(pending.has('a:1|funnel')).toBe(true))
    act(() => pending.get('a:1|funnel')?.(heatmapFor('a:1')))
    await waitFor(() => expect(result.current.heatmap).not.toBeNull())

    rerender({ id: 'b:1' })

    expect(result.current.heatmap).toBeNull()
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(aborted).toContain('a:1|funnel'))
  })

  it('reports a failure without losing the page it belongs to', async () => {
    const failing: HeatmapPort = { explain: () => Promise.reject({ code: 'not_found', message: 'No such page.' }) }
    const { result } = renderHook(() => usePageExplanation(failing, 'a:1', 'funnel'))

    await waitFor(() => expect(result.current.error?.code).toBe('not_found'))
    expect(result.current.heatmap).toBeNull()
    expect(result.current.loading).toBe(false)
  })
})
