import { count, fileNameOf } from '../../domain/format'
import type { IndexProgress } from '../../domain/indexing'

interface IndexingBannerProps {
  progress: IndexProgress
}

export function IndexingBanner({ progress }: IndexingBannerProps) {
  const fileName = fileNameOf(progress.currentPath)
  const message =
    progress.pagesEmbedded > 0
      ? `Reading page ${progress.pagesEmbedded} of ${progress.pagesIndexed}.`
      : `Indexing. ${count(progress.filesIndexed, 'file')}, ${count(progress.pagesIndexed, 'page')} so far.`

  return (
    <div role="status" className="flex items-baseline gap-3 border-b border-border py-3 text-sm">
      <span className="shrink-0 text-ink">{message}</span>
      {fileName && <span className="min-w-0 truncate font-mono text-xs text-ink-muted">{fileName}</span>}
    </div>
  )
}
