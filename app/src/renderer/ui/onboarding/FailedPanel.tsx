import { Screen } from '../shared/Screen'
import { Button } from '../shared/Button'

interface FailedPanelProps {
  reason: string
  onRestart: () => void
}

export function FailedPanel({ reason, onRestart }: FailedPanelProps) {
  return (
    <Screen>
      <p className="text-lg text-ink">The local engine could not start.</p>
      <p className="mt-2 text-sm text-status-error">{reason}</p>
      <div className="mt-8">
        <Button onClick={onRestart}>Restart engine</Button>
      </div>
    </Screen>
  )
}
