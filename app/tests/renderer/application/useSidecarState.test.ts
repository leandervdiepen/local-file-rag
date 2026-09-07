// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useSidecarState } from '../../../src/renderer/application/useSidecarState'
import { createFakeSidecarPort } from '../../fakes/fake-sidecar-port'

describe('useSidecarState', () => {
  it('starts in the starting state', () => {
    const port = createFakeSidecarPort()
    const { result } = renderHook(() => useSidecarState(port))
    expect(result.current.state).toEqual({ status: 'starting' })
  })

  it('follows state pushed by the port', () => {
    const port = createFakeSidecarPort()
    const { result } = renderHook(() => useSidecarState(port))

    act(() => {
      port.emit({ status: 'ready', baseUrl: 'http://127.0.0.1:5555' })
    })

    expect(result.current.state).toEqual({ status: 'ready', baseUrl: 'http://127.0.0.1:5555' })
  })

  it('ignores an illegal transition pushed by the port', () => {
    const port = createFakeSidecarPort()
    const { result } = renderHook(() => useSidecarState(port))

    act(() => {
      port.emit({ status: 'ready', baseUrl: 'http://127.0.0.1:5555' })
    })
    act(() => {
      port.emit({ status: 'starting' })
    })

    expect(result.current.state).toEqual({ status: 'ready', baseUrl: 'http://127.0.0.1:5555' })
  })

  it('calls restart on the port', async () => {
    const port = createFakeSidecarPort()
    const { result } = renderHook(() => useSidecarState(port))

    await act(async () => {
      await result.current.restart()
    })

    expect(port.restartCalls).toBe(1)
  })

  it('stops listening once unmounted', () => {
    const port = createFakeSidecarPort()
    const { unmount, result } = renderHook(() => useSidecarState(port))
    unmount()

    act(() => {
      port.emit({ status: 'ready', baseUrl: 'http://127.0.0.1:1' })
    })

    expect(result.current.state).toEqual({ status: 'starting' })
  })
})
