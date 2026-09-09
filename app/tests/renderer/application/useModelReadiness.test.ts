// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { HealthPort } from '../../../src/renderer/application/ports'
import { useModelReadiness } from '../../../src/renderer/application/useModelReadiness'
import type { ModelReadiness } from '../../../src/renderer/domain/model-readiness'

const POLL = 5

function reading(...answers: (ModelReadiness | Error)[]) {
  let asked = 0
  const port: HealthPort & { asked: () => number } = {
    asked: () => asked,
    readiness: () => {
      const answer = answers[Math.min(asked, answers.length - 1)]
      asked += 1
      return answer instanceof Error ? Promise.reject(answer) : Promise.resolve(answer)
    },
  }
  return port
}

const DOWNLOADING: ModelReadiness = { state: 'downloading', bytesDone: 1, bytesTotal: 4, fraction: 0.25 }
const READY: ModelReadiness = { state: 'ready', bytesDone: 0, bytesTotal: 0, fraction: null }

describe('useModelReadiness', () => {
  it('reports what the sidecar says', async () => {
    const port = reading(DOWNLOADING)
    const { result } = renderHook(() => useModelReadiness(port, POLL))

    await waitFor(() => expect(result.current.state).toBe('downloading'))
    expect(result.current.fraction).toBe(0.25)
  })

  it('keeps asking until the model is ready', async () => {
    const port = reading(DOWNLOADING, DOWNLOADING, READY)
    const { result } = renderHook(() => useModelReadiness(port, POLL))

    await waitFor(() => expect(result.current.state).toBe('ready'))
    expect(port.asked()).toBe(3)
  })

  it('stops asking once the model is ready, so the sidecar never looks busy', async () => {
    const port = reading(READY)
    renderHook(() => useModelReadiness(port, POLL))

    await waitFor(() => expect(port.asked()).toBe(1))
    await new Promise((resolve) => setTimeout(resolve, POLL * 8))
    expect(port.asked()).toBe(1)
  })

  it('keeps asking through a sidecar that is restarting', async () => {
    const port = reading(new Error('connection refused'), READY)
    const { result } = renderHook(() => useModelReadiness(port, POLL))

    await waitFor(() => expect(result.current.state).toBe('ready'))
  })
})
