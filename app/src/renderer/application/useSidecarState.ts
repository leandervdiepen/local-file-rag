import { useCallback, useEffect, useReducer } from 'react'
import { initialSidecarState, sidecarStateReducer, type SidecarState } from '../domain/sidecar-state'
import type { SidecarPort } from './ports'

export interface UseSidecarState {
  state: SidecarState
  restart: () => Promise<void>
}

/** Tracks what the sidecar is doing. A stale or illegal event never moves the UI backwards. */
export function useSidecarState(port: SidecarPort): UseSidecarState {
  const [state, dispatch] = useReducer(sidecarStateReducer, initialSidecarState)

  useEffect(() => port.subscribe(dispatch), [port])

  const restart = useCallback(() => port.restart(), [port])

  return { state, restart }
}
