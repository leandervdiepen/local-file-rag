import { useState } from 'react'
import type { NativeActionsPort } from '../../application/ports'
import type { SearchError } from '../../domain/search-state'
import { Button } from '../shared/Button'
import { Screen } from '../shared/Screen'

interface FirstRunPanelProps {
  nativeActions: NativeActionsPort
  onAddFolder: (path: string) => Promise<void>
  error: SearchError | null
}

export function FirstRunPanel({ nativeActions, onAddFolder, error }: FirstRunPanelProps) {
  const [adding, setAdding] = useState(false)

  async function chooseFolder(): Promise<void> {
    const folder = await nativeActions.pickFolder()
    if (!folder) return
    setAdding(true)
    try {
      await onAddFolder(folder)
    } finally {
      setAdding(false)
    }
  }

  return (
    <Screen>
      <p className="text-lg text-ink">Pick a folder to search.</p>
      <p className="mt-2 text-sm text-ink-muted">
        Everything is read and stored on this Mac. Indexing runs in the background and search works while it does.
      </p>
      <div className="mt-8">
        <Button onClick={() => void chooseFolder()} disabled={adding}>
          {adding ? 'Adding folder' : 'Choose folder'}
        </Button>
      </div>
      {error && <p className="mt-4 text-sm text-status-error">{error.message}</p>}
    </Screen>
  )
}
