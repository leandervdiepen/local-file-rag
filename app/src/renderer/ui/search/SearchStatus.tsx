import { formatMillis } from '../../domain/format'
import type { IndexStats } from '../../domain/indexing'
import type { SearchState } from '../../domain/search-state'

interface SearchStatusProps {
  state: SearchState
  stats: IndexStats | null
  resultCount: number
}

/**
 * The line under the search box, and the whole screen when there is no list.
 *
 * Every branch here is one of the states `docs/conventions/design.md` requires
 * a screen to have drawn before it is done: empty, loaded, no results, error.
 */
export function SearchStatus({ state, stats, resultCount }: SearchStatusProps) {
  if (state.phase === 'error') {
    return <p className="py-3 text-sm text-status-error">{state.error?.message}</p>
  }

  if (state.phase === 'idle') {
    return (
      <p className="py-3 text-sm text-ink-muted">
        {stats ? `${stats.filesTextIndexed} files ready. Start typing.` : 'Start typing.'}
      </p>
    )
  }

  if (resultCount === 0 && state.phase === 'done') {
    return (
      <p className="py-3 text-sm text-ink-muted">
        Nothing matched. Try a word from the file name, or from the text on the page.
      </p>
    )
  }

  const reading = state.phase === 'reading' && state.reading && state.reading.pagesTotal > 0

  return (
    <p className="py-3 text-sm text-ink-muted" aria-live="polite">
      {resultCount} {resultCount === 1 ? 'page' : 'pages'}
      {state.tookMs === null ? '' : ` in ${formatMillis(state.tookMs)}`}
      {reading && state.reading ? `. Reading page ${state.reading.pagesRead} of ${state.reading.pagesTotal}.` : ''}
    </p>
  )
}
