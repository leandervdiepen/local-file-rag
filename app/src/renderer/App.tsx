import { useMemo } from 'react'
import { createNativeActionsPort, createSidecarPort } from './infrastructure/bridge-adapter'
import { useSidecarState } from './application/useSidecarState'
import { SidecarStateView } from './ui/onboarding/SidecarStateView'
import { ReadyShell } from './ui/shell/ReadyShell'

/** Composition root: the only place that wires a use case to its adapters. */
export function App() {
  const sidecarPort = useMemo(() => createSidecarPort(), [])
  const nativeActions = useMemo(() => createNativeActionsPort(), [])
  const { state, restart } = useSidecarState(sidecarPort)

  if (state.status === 'ready') {
    return (
      <ReadyShell
        baseUrl={state.baseUrl}
        token={sidecarPort.getConnectionInfo().token}
        nativeActions={nativeActions}
      />
    )
  }

  return <SidecarStateView state={state} onRestart={restart} nativeActions={nativeActions} />
}
