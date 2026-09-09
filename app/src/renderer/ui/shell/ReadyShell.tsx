import { useMemo } from 'react'

// Until the settings screen exists, every answer uses the free default (D38).
const DEFAULT_MODEL_ID = 'openrouter/free'
import type { NativeActionsPort } from '../../application/ports'
import { useIndexing } from '../../application/useIndexing'
import { createChatPort } from '../../infrastructure/chat-adapter'
import { createFoldersPort } from '../../infrastructure/folders-adapter'
import { createHeatmapPort } from '../../infrastructure/heatmap-adapter'
import { createIndexPort } from '../../infrastructure/index-adapter'
import { createPageImagePort } from '../../infrastructure/page-image-adapter'
import { createSearchPort } from '../../infrastructure/search-adapter'
import { createSidecarClient } from '../../infrastructure/sidecar-client'
import { FirstRunPanel } from '../onboarding/FirstRunPanel'
import { SearchScreen } from '../search/SearchScreen'

interface ReadyShellProps {
  baseUrl: string
  token: string
  nativeActions: NativeActionsPort
}

/**
 * Everything that needs a running sidecar, and the choice between the two
 * screens that exist: onboarding until a folder is indexed, search after.
 *
 * The clients are built from the ready state's base URL rather than the one
 * the preload bridge captured at launch, because the port is only known once
 * the handshake has happened.
 */
export function ReadyShell({ baseUrl, token, nativeActions }: ReadyShellProps) {
  const client = useMemo(() => createSidecarClient({ baseUrl, token }), [baseUrl, token])
  const foldersPort = useMemo(() => createFoldersPort(client), [client])
  const indexPort = useMemo(() => createIndexPort(client), [client])
  const searchPort = useMemo(() => createSearchPort(client), [client])
  const pageImages = useMemo(() => createPageImagePort(client), [client])
  const heatmaps = useMemo(() => createHeatmapPort(client), [client])
  const chat = useMemo(() => createChatPort(client), [client])

  const { folders, progress, stats, error, loaded, addFolder } = useIndexing(foldersPort, indexPort)

  if (!loaded) return null
  if (folders.length === 0) {
    return <FirstRunPanel nativeActions={nativeActions} onAddFolder={addFolder} error={error} />
  }

  return (
    <SearchScreen
      search={searchPort}
      pageImages={pageImages}
      heatmaps={heatmaps}
      chat={chat}
      modelId={DEFAULT_MODEL_ID}
      nativeActions={nativeActions}
      progress={progress}
      stats={stats}
    />
  )
}
