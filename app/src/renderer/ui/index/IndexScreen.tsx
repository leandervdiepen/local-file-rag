import { useEffect, useState } from 'react'
import type { IndexPort } from '../../application/ports'
import { count, formatBytes } from '../../domain/format'
import type { FolderFailure, IndexedFolder, IndexStats } from '../../domain/indexing'
import { labelSkip, skipsByCount, type IndexedFileRow } from '../../domain/skip-reasons'
import { Button } from '../shared/Button'
import { OverlayScreen } from '../shared/OverlayScreen'
import { Section } from '../shared/Section'
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
    <OverlayScreen title="Index" onClose={onClose} actions={<Button onClick={onRescan}>Rescan</Button>}>
      {stats && (
        <dl className="mt-8 grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-4">
          <Figure label="Files indexed" value={stats.filesTextIndexed.toLocaleString()} />
          <Figure label="Pages" value={stats.pagesTotal.toLocaleString()} />
          <Figure label="Pages read by the model" value={stats.pagesEmbedded.toLocaleString()} />
          <Figure label="On disk" value={formatBytes(stats.bytesOnDisk)} />
        </dl>
      )}

      {failures.length > 0 && (
        <div className="mt-8">
          <FolderProblems failures={failures} />
        </div>
      )}

      <Section title="Folders" hint="A folder that is off stops appearing in results. Its files stay indexed, so turning it back on is instant.">
        <FolderList folders={folders} onToggle={onToggleFolder} onRemove={onRemoveFolder} />
        <div className="mt-3">
          <Button onClick={onAddFolder}>Add folder</Button>
        </div>
      </Section>

      {stats && stats.filesSkipped === 0 && <p className="mt-10 text-sm text-ink-muted">Every file was indexed.</p>}

      {stats && stats.filesSkipped > 0 && (
        <Section title={count(stats.filesSkipped, 'skipped file')}>
          <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-muted">
            {skipsByCount(stats.skipsByReason).map(({ reason, count: n }) => (
              <li key={reason}>
                <span className="font-mono tabular-nums text-ink">{n.toLocaleString()}</span> {labelSkip(reason)}
              </li>
            ))}
          </ul>
          <SkippedFiles files={skipped} onForget={forget} />
        </Section>
      )}
    </OverlayScreen>
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
