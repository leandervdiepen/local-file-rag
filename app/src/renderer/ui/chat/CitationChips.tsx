import type { RetrievedPage } from '../../domain/chat'
import { fileNameOf } from '../../domain/format'

interface CitationChipsProps {
  pages: RetrievedPage[]
  onOpen: (page: RetrievedPage) => void
}

/** The pages the answer cited. Clicking one opens it with the heatmap that explains it. */
export function CitationChips({ pages, onOpen }: CitationChipsProps) {
  return (
    <ul className="mt-5 flex flex-wrap gap-1.5" aria-label="Cited pages">
      {pages.map((page) => {
        const fileName = fileNameOf(page.path)
        return (
          <li key={page.pageId} className="max-w-full">
            <button
              type="button"
              onClick={() => onOpen(page)}
              title={page.path}
              aria-label={`Open ${fileName}, page ${page.pageNo}`}
              className="focus-ring max-w-full truncate rounded-control bg-surface px-2 py-1 font-mono text-xs text-ink-muted shadow-control transition-colors hover:text-ink"
            >
              [{page.index}] {fileName} p. {page.pageNo}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
