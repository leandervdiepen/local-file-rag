import { useCallback, useEffect, useState } from 'react'
import type { IndexedFolder, IndexProgress, IndexStats } from '../domain/indexing'
import { asSearchError, type SearchError } from '../domain/search-state'
import type { FoldersPort, IndexPort } from './ports'

export interface UseIndexing {
  folders: IndexedFolder[]
  progress: IndexProgress | null
  stats: IndexStats | null
  error: SearchError | null
  loaded: boolean
  addFolder: (path: string) => Promise<void>
  setFolderEnabled: (id: string, enabled: boolean) => Promise<void>
  removeFolder: (id: string) => Promise<void>
  rescan: () => Promise<void>
}

/**
 * Owns the folders being indexed and the crawl running over them.
 *
 * Progress is watched from mount, not only after a folder is added, because
 * the window can be closed and reopened while a crawl keeps running in the
 * sidecar. The stream resolves immediately when no job exists, so watching
 * costs nothing in the ordinary case.
 */
export function useIndexing(foldersPort: FoldersPort, indexPort: IndexPort): UseIndexing {
  const [folders, setFolders] = useState<IndexedFolder[]>([])
  const [progress, setProgress] = useState<IndexProgress | null>(null)
  const [error, setError] = useState<SearchError | null>(null)
  const [stats, setStats] = useState<IndexStats | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [watching, setWatching] = useState(0)

  useEffect(() => {
    let live = true
    foldersPort
      .list()
      .then((found) => {
        if (live) setFolders(found)
      })
      .catch((cause: unknown) => {
        if (live) setError(asSearchError(cause))
      })
      .finally(() => {
        if (live) setLoaded(true)
      })
    return () => {
      live = false
    }
  }, [foldersPort])

  useEffect(() => {
    const controller = new AbortController()
    indexPort.watchProgress(setProgress, controller.signal).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(asSearchError(cause))
    })
    return () => controller.abort()
  }, [indexPort, watching])

  const finished = progress?.done ?? false
  useEffect(() => {
    let live = true
    indexPort
      .stats()
      .then((next) => {
        if (live) setStats(next)
      })
      .catch(() => undefined)
    return () => {
      live = false
    }
    // `finished` is a dependency so the counts refresh the moment a crawl ends.
    // Nothing else changes them, and the banner already carries the live totals.
  }, [indexPort, finished])

  const addFolder = useCallback(
    async (path: string) => {
      setError(null)
      try {
        const added = await foldersPort.add(path)
        setFolders((current) => (current.some((f) => f.id === added.id) ? current : [...current, added]))
        await indexPort.rescan()
        setWatching((count) => count + 1)
      } catch (cause: unknown) {
        setError(asSearchError(cause))
      }
    },
    [foldersPort, indexPort],
  )

  const setFolderEnabled = useCallback(
    async (id: string, enabled: boolean) => {
      setError(null)
      // Optimistic, because the switch has to move under the finger. A failure
      // puts it back and says why, which is the only honest way to show a
      // toggle whose real state lives in another process.
      setFolders((current) => current.map((folder) => (folder.id === id ? { ...folder, enabled } : folder)))
      try {
        const updated = await foldersPort.setEnabled(id, enabled)
        setFolders((current) => current.map((folder) => (folder.id === id ? updated : folder)))
      } catch (cause: unknown) {
        setFolders((current) => current.map((folder) => (folder.id === id ? { ...folder, enabled: !enabled } : folder)))
        setError(asSearchError(cause))
      }
    },
    [foldersPort],
  )

  const removeFolder = useCallback(
    async (id: string) => {
      setError(null)
      try {
        await foldersPort.remove(id)
        setFolders((current) => current.filter((folder) => folder.id !== id))
      } catch (cause: unknown) {
        setError(asSearchError(cause))
      }
    },
    [foldersPort],
  )

  const rescan = useCallback(async () => {
    setError(null)
    try {
      await indexPort.rescan()
      setWatching((count) => count + 1)
    } catch (cause: unknown) {
      setError(asSearchError(cause))
    }
  }, [indexPort])

  return { folders, progress, stats, error, loaded, addFolder, setFolderEnabled, removeFolder, rescan }
}
