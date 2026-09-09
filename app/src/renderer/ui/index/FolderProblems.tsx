import { shortenHomePath } from '../../domain/format'
import type { FolderFailure } from '../../domain/indexing'

interface FolderProblemsProps {
  failures: FolderFailure[]
}

/**
 * The folders the last crawl could not read.
 *
 * Shown after the crawl ends, not only while it runs, because the whole point
 * is a result list that looks complete and is not. The reason comes from the
 * sidecar and names the setting to change, so nothing is restated here.
 */
export function FolderProblems({ failures }: FolderProblemsProps) {
  if (failures.length === 0) return null

  return (
    <div className="border-b border-border py-3" role="alert">
      {failures.map((failure) => (
        <p key={failure.path} className="text-sm text-ink">
          <span className="font-mono text-xs text-status-error">{shortenHomePath(failure.path)}</span>{' '}
          <span className="text-ink-muted">{failure.reason}</span>
        </p>
      ))}
    </div>
  )
}
