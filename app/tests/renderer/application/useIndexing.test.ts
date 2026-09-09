// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { FoldersPort, IndexPort } from '../../../src/renderer/application/ports'
import { useIndexing } from '../../../src/renderer/application/useIndexing'
import type { IndexedFolder } from '../../../src/renderer/domain/indexing'

const DOCUMENTS: IndexedFolder = { id: 'f1', path: '/Users/x/Documents', enabled: true, addedAt: '2026-09-09' }

/** A real folders port over an in-memory list, with a switch to make one call fail. */
function createFoldersPort(initial: IndexedFolder[] = [DOCUMENTS]) {
  let folders = [...initial]
  const port: FoldersPort & { refuseNext: boolean } = {
    refuseNext: false,
    list: () => Promise.resolve([...folders]),
    add: (path) => {
      const added = { id: path, path, enabled: true, addedAt: '2026-09-09' }
      folders = [...folders, added]
      return Promise.resolve(added)
    },
    remove: (id) => {
      folders = folders.filter((folder) => folder.id !== id)
      return Promise.resolve()
    },
    setEnabled: (id, enabled) => {
      if (port.refuseNext) return Promise.reject(new Error('the sidecar said no'))
      folders = folders.map((folder) => (folder.id === id ? { ...folder, enabled } : folder))
      return Promise.resolve(folders.find((folder) => folder.id === id)!)
    },
  }
  return port
}

const indexPort: IndexPort = {
  rescan: () => Promise.resolve(),
  stats: () => new Promise(() => undefined),
  files: () => Promise.resolve({ files: [], nextCursor: null }),
  forget: () => Promise.resolve(),
  watchProgress: () => Promise.resolve(),
}

describe('useIndexing', () => {
  it('loads the folders that are already indexed', async () => {
    // The port is built once: `useIndexing` keys its effects on identity, so a
    // fresh one per render would reload forever.
    const folders = createFoldersPort()
    const { result } = renderHook(() => useIndexing(folders, indexPort))

    await waitFor(() => expect(result.current.loaded).toBe(true))
    expect(result.current.folders).toEqual([DOCUMENTS])
  })

  it('turns a folder off and keeps it in the list', async () => {
    const folders = createFoldersPort()
    const { result } = renderHook(() => useIndexing(folders, indexPort))
    await waitFor(() => expect(result.current.loaded).toBe(true))

    await act(async () => {
      await result.current.setFolderEnabled('f1', false)
    })

    expect(result.current.folders).toEqual([{ ...DOCUMENTS, enabled: false }])
  })

  it('puts the switch back and says why when the sidecar refuses', async () => {
    const folders = createFoldersPort()
    const { result } = renderHook(() => useIndexing(folders, indexPort))
    await waitFor(() => expect(result.current.loaded).toBe(true))
    folders.refuseNext = true

    await act(async () => {
      await result.current.setFolderEnabled('f1', false)
    })

    expect(result.current.folders[0].enabled).toBe(true)
    expect(result.current.error).not.toBeNull()
  })

  it('removing a folder takes it out of the list', async () => {
    const folders = createFoldersPort()
    const { result } = renderHook(() => useIndexing(folders, indexPort))
    await waitFor(() => expect(result.current.loaded).toBe(true))

    await act(async () => {
      await result.current.removeFolder('f1')
    })

    expect(result.current.folders).toEqual([])
  })
})
