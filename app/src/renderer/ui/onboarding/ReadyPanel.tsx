import { useState } from 'react'
import { Screen } from '../shared/Screen'
import { Button } from '../shared/Button'
import type { NativeActionsPort } from '../../application/ports'

interface ReadyPanelProps {
  baseUrl: string
  nativeActions: NativeActionsPort
}

export function ReadyPanel({ baseUrl, nativeActions }: ReadyPanelProps) {
  const [chosenFolder, setChosenFolder] = useState<string | null>(null)

  async function handleChooseFolder(): Promise<void> {
    const folder = await nativeActions.pickFolder()
    if (folder) setChosenFolder(folder)
  }

  return (
    <Screen>
      <p className="text-lg text-ink">The local engine is ready.</p>
      <p className="mt-2 font-mono text-sm text-ink-muted">{baseUrl}</p>
      <p className="mt-8 text-sm text-ink-muted">Add a folder to start indexing.</p>
      <div className="mt-4">
        <Button onClick={() => void handleChooseFolder()}>Choose folder</Button>
      </div>
      {chosenFolder && (
        <p className="mt-4 truncate font-mono text-xs text-ink-muted" title={chosenFolder}>
          {chosenFolder}
        </p>
      )}
    </Screen>
  )
}
