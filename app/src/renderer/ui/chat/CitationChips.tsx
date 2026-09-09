import type { RetrievedPage } from '../../domain/chat'

interface CitationChipsProps {
  pages: RetrievedPage[]
  onOpen: (page: RetrievedPage) => void
}

function fileNameOf(path: string): string {
  const separator = path.lastIndexOf('/')
  return separator === -1 ? path : path.slice(separator + 1)
}

/** The pages the answer cited. Clicking one opens it with the heatmap that explains it. */
export function CitationChips({ pages, onOpen }: CitationChipsProps) {
  return (
    <div className="mt-5 flex flex-wrap gap-2">
      {pages.map((page) => (
        <button
          key={page.pageId}
          type="button"
          onClick={() => onOpen(page)}
          title={page.path}
          className="max-w-full truncate rounded-control border border-border px-2 py-1 font-mono text-xs text-ink-muted hover:bg-border/50 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          [{page.index}] {fileNameOf(page.path)} p{page.pageNo}
        </button>
      ))}
    </div>
  )
}
