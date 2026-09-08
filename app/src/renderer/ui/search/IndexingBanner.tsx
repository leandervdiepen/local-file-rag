import type { IndexProgress } from '../../domain/indexing'

interface IndexingBannerProps {
  progress: IndexProgress
}

export function IndexingBanner({ progress }: IndexingBannerProps) {
  const fileName = progress.currentPath.slice(progress.currentPath.lastIndexOf('/') + 1)

  return (
    <div className="flex items-baseline gap-3 border-b border-border py-3 text-sm" aria-live="polite">
      <span className="text-ink">
        {progress.pagesEmbedded > 0
          ? `Reading pages. ${progress.pagesEmbedded} of ${progress.pagesIndexed}.`
          : `Indexing. ${progress.filesIndexed} files, ${progress.pagesIndexed} pages.`}
      </span>
      {fileName && <span className="truncate font-mono text-xs text-ink-muted">{fileName}</span>}
    </div>
  )
}
