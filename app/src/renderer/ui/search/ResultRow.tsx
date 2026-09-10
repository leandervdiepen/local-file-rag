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

const WHY_NO_SNIPPET: Record<string, string> = {
  filename: 'Matched the file name',
  visual: 'Matched what the page looks like',
}

export function ResultRow({ hit, selected, pageImages, actions, onSelect }: ResultRowProps) {
  return (
    <li
      id={`result-${hit.pageId}`}
      role="option"
      aria-selected={selected}
      onClick={() => onSelect(hit.pageId)}
      onDoubleClick={() => actions.open(hit.path)}
      className={`flex cursor-default items-start gap-3 rounded-control px-3 py-2 ${selected ? 'bg-accent/10' : 'hover:bg-border/30'}`}
    >
      <PageThumbnail pageId={hit.pageId} pageImages={pageImages} />

      <div className="flex min-w-0 flex-1 flex-col gap-0.5 py-0.5">
        {hit.kind === 'pdf' && <p className="font-mono text-xs text-ink-muted">Page {hit.pageNo}</p>}
        {hit.snippet ? (
          <p className="line-clamp-2 text-sm text-ink">{hit.snippet}</p>
        ) : (
          // A snippet is its own explanation. Only a page with no matching
          // words needs to be told why it is here.
          <p className="text-sm text-ink-muted">{WHY_NO_SNIPPET[hit.stage] ?? ''}</p>
        )}
      </div>

      {selected && (
        // tabIndex -1 keeps the listbox valid and the hand on the keyboard:
        // arrow keys never leave the search input, so these are for the mouse
        // and the shortcuts they show are for everyone else.
        <div className="flex shrink-0 items-center gap-0.5 self-center">
          <RowAction label="Open" keys="↩" shortcut="Enter" onClick={() => actions.open(hit.path)} />
          <RowAction label="Reveal" keys="⌘↩" shortcut="Meta+Enter" onClick={() => actions.reveal(hit.path)} />
          <RowAction label="Copy path" keys="⇧⌘C" shortcut="Shift+Meta+C" onClick={() => actions.copyPath(hit.path)} />
        </div>
      )}
    </li>
  )
}

interface RowActionProps {
  label: string
  keys: string
  shortcut: string
  onClick: () => void
}

function RowAction({ label, keys, shortcut, onClick }: RowActionProps) {
  return (
    <button
      type="button"
      tabIndex={-1}
      aria-keyshortcuts={shortcut}
      onClick={onClick}
      className="focus-ring flex items-baseline gap-1.5 rounded-control px-2 py-1 text-xs text-ink-muted transition-colors hover:bg-border/40 hover:text-ink"
    >
      {label}
      <kbd aria-hidden className="font-sans text-ink-muted/70">
        {keys}
      </kbd>
    </button>
  )
}
