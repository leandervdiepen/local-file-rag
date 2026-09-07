import type { PageImagePort } from '../../application/ports'
import type { PageHit } from '../../domain/search-results'
import { PageThumbnail } from './PageThumbnail'

export interface ResultActions {
  open: (path: string) => void
  reveal: (path: string) => void
  copyPath: (path: string) => void
}

interface ResultRowProps {
  hit: PageHit
  selected: boolean
  pageImages: PageImagePort
  actions: ResultActions
  onSelect: (pageId: string) => void
}

const ACTION_CLASS =
  'rounded-control px-2 py-1 text-xs text-ink-muted hover:bg-border/50 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent'

export function ResultRow({ hit, selected, pageImages, actions, onSelect }: ResultRowProps) {
  return (
    <li
      id={`result-${hit.pageId}`}
      role="option"
      aria-selected={selected}
      onClick={() => onSelect(hit.pageId)}
      onDoubleClick={() => actions.open(hit.path)}
      className={`flex cursor-default items-start gap-4 rounded-control px-3 py-3 ${selected ? 'bg-accent/10' : ''}`}
    >
      <PageThumbnail pageId={hit.pageId} pageImages={pageImages} />

      <div className="min-w-0 flex-1">
        {hit.kind === 'pdf' && <p className="font-mono text-xs text-ink-muted">Page {hit.pageNo}</p>}
        {hit.snippet && <p className="mt-1 line-clamp-2 text-sm text-ink">{hit.snippet}</p>}
      </div>

      {selected && (
        // tabIndex -1 keeps the listbox valid and the hand on the keyboard:
        // arrow keys never leave the search input, so these are for the mouse
        // and the shortcuts in SearchBox are for everyone else.
        <div className="flex shrink-0 items-center gap-1">
          <button type="button" tabIndex={-1} className={ACTION_CLASS} onClick={() => actions.open(hit.path)}>
            Open
          </button>
          <button type="button" tabIndex={-1} className={ACTION_CLASS} onClick={() => actions.reveal(hit.path)}>
            Reveal
          </button>
          <button type="button" tabIndex={-1} className={ACTION_CLASS} onClick={() => actions.copyPath(hit.path)}>
            Copy path
          </button>
        </div>
      )}
    </li>
  )
}
