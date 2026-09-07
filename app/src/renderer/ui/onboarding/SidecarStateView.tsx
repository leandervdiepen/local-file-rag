import type { SidecarState } from '../../domain/sidecar-state'
import type { NativeActionsPort } from '../../application/ports'
import { StartingPanel } from './StartingPanel'
import { ReadyPanel } from './ReadyPanel'
import { CrashedPanel } from './CrashedPanel'
import { FailedPanel } from './FailedPanel'

interface SidecarStateViewProps {
  state: SidecarState
  onRestart: () => void
  nativeActions: NativeActionsPort
}

/** Renders whichever sidecar state is current. Nothing here decides; it displays. */
export function SidecarStateView({ state, onRestart, nativeActions }: SidecarStateViewProps) {
  switch (state.status) {
    case 'starting':
      return <StartingPanel />
    case 'ready':
      return <ReadyPanel baseUrl={state.baseUrl} nativeActions={nativeActions} />
    case 'crashed':
      return (
        <CrashedPanel
          reason={state.reason}
          attempt={state.attempt}
          maxAttempts={state.maxAttempts}
          onRestart={onRestart}
        />
      )
    case 'failed':
      return <FailedPanel reason={state.reason} onRestart={onRestart} />
  }
}
