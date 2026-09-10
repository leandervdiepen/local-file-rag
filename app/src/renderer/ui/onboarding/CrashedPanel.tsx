import { Screen } from '../shared/Screen'
import { Button } from '../shared/Button'

interface CrashedPanelProps {
  reason: string
  attempt: number
  maxAttempts: number
  onRestart: () => void
}

export function CrashedPanel({ reason, attempt, maxAttempts, onRestart }: CrashedPanelProps) {
  return (
    <Screen>
      <h1 className="text-lg font-medium text-ink">The local engine stopped</h1>
      <p className="mt-2 text-sm text-status-error">{reason}</p>
      <p role="status" className="mt-2 text-sm text-ink-muted">
        Retrying, attempt {attempt} of {maxAttempts}.
      </p>
      <div className="mt-8">
        <Button onClick={onRestart}>Restart now</Button>
      </div>
    </Screen>
  )
}
