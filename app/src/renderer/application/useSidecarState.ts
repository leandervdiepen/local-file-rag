import { useCallback, useEffect, useReducer } from 'react'
import { initialSidecarState, sidecarStateReducer, type SidecarState } from '../domain/sidecar-state'
import type { SidecarPort } from './ports'

export interface UseSidecarState {
  state: SidecarState
  restart: () => Promise<void>
}

/** The use case: know what the sidecar is doing, and offer a way to restart it. */
export function useSidecarState(port: SidecarPort): UseSidecarState {
  const [state, dispatch] = useReducer(sidecarStateReducer, initialSidecarState)

  useEffect(() => port.subscribe(dispatch), [port])

  const restart = useCallback(() => port.restart(), [port])

  return { state, restart }
}
