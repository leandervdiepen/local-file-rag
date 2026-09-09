import { useEffect, useState } from 'react'
import type { IndexPort } from '../../application/ports'
import { formatBytes } from '../../domain/format'
import type { FolderFailure, IndexedFolder, IndexStats } from '../../domain/indexing'
import { skipsByCount, type IndexedFileRow } from '../../domain/skip-reasons'
import { Button } from '../shared/Button'
import { FolderList } from './FolderList'
import { FolderProblems } from './FolderProblems'
import { SkippedFiles } from './SkippedFiles'

interface IndexScreenProps {
  index: IndexPort
  folders: IndexedFolder[]
  failures: FolderFailure[]
  onRescan: () => void
  onAddFolder: () => void
  onToggleFolder: (id: string, enabled: boolean) => void
  onRemoveFolder: (id: string) => void
  onClose: () => void
}

/**
 * What is indexed, what is not, and why.
 *
 * The whole screen exists so a person can trust the search: a result list can
 * only be believed by someone who knows what was left out. So the skipped
 * files are not an error log tucked away, they are half the page.
 */
export function IndexScreen({
  index,
  folders,
  failures,
  onRescan,
  onAddFolder,
  onToggleFolder,
  onRemoveFolder,
  onClose,
}: IndexScreenProps) {
  const [stats, setStats] = useState<IndexStats | null>(null)
  const [skipped, setSkipped] = useState<IndexedFileRow[]>([])

  useEffect(() => {
    let live = true
    void index.stats().then((next) => live && setStats(next))
    void index.files('skipped', null).then((page) => live && setSkipped(page.files))
    return () => {
      live = false
    }
  }, [index])

  async function forget(fileId: string): Promise<void> {
    // The row goes first. It is the user's own action, and a list that waits
    // for a round trip before acknowledging a click feels broken.
    setSkipped((current) => current.filter((file) => file.id !== fileId))
    await index.forget(fileId)
    setStats(await index.stats())
  }

  return (
    <section className="fixed inset-0 z-10 overflow-auto bg-surface" aria-label="Index">
      <div className="mx-auto w-full max-w-3xl px-8 py-12">
        <header className="flex items-start gap-4">
          <h1 className="flex-1 text-lg text-ink">Your index</h1>
          <Button onClick={onRescan}>Rescan</Button>
          <Button onClick={onClose}>Close</Button>
        </header>

        {stats && (
          <dl className="mt-8 grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-4">
            <Figure label="Files indexed" value={stats.filesTextIndexed.toLocaleString()} />
            <Figure label="Pages" value={stats.pagesTotal.toLocaleString()} />
            <Figure label="Pages read by the model" value={stats.pagesEmbedded.toLocaleString()} />
            <Figure label="Storage" value={formatBytes(stats.bytesOnDisk)} />
          </dl>
        )}

        <div className="mt-8">
          <FolderProblems failures={failures} />
        </div>

        <h2 className="mt-12 text-sm text-ink">Folders</h2>
        <p className="mt-1 text-xs text-ink-muted">
          A folder that is off keeps its files in the index and stops being watched for changes.
        </p>
        <FolderList folders={folders} onToggle={onToggleFolder} onRemove={onRemoveFolder} />
        <div className="mt-3">
          <Button onClick={onAddFolder}>Add folder</Button>
        </div>

        {stats && (
          <>
            <h2 className="mt-12 text-sm text-ink">
              {stats.filesSkipped.toLocaleString()} files were not indexed
            </h2>
            <ul className="mt-3 text-sm text-ink-muted">
              {skipsByCount(stats.skipsByReason).map(({ reason, count }) => (
                <li key={reason} className="py-1">
                  <span className="font-mono tabular-nums">{count.toLocaleString()}</span> {reason.replaceAll('_', ' ')}
                </li>
              ))}
            </ul>
            <SkippedFiles files={skipped} onForget={forget} />
          </>
        )}
      </div>
    </section>
  )
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="mt-1 font-mono text-lg tabular-nums text-ink">{value}</dd>
    </div>
  )
}
