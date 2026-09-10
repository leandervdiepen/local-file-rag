import { count, formatMillis } from '../../domain/format'
import type { IndexStats } from '../../domain/indexing'
import type { SearchState } from '../../domain/search-state'

interface SearchStatusProps {
  state: SearchState
  stats: IndexStats | null
  resultCount: number
}

interface Status {
  text: string
  tone: 'muted' | 'error'
}

/**
 * The line under the search box, and the whole screen when there is no list.
 *
 * Every branch here is one of the states `docs/conventions/design.md` requires
 * a screen to have drawn before it is done: empty, loaded, no results, error.
 * It is one live region that changes its words, so a screen reader hears
 * every one of them, including the search that found nothing.
 */
export function SearchStatus({ state, stats, resultCount }: SearchStatusProps) {
  const { text, tone } = describe(state, stats, resultCount)

  return (
    <p role="status" className={`py-3 text-sm ${tone === 'error' ? 'text-status-error' : 'text-ink-muted'}`}>
      {text}
    </p>
  )
}

function describe(state: SearchState, stats: IndexStats | null, resultCount: number): Status {
  if (state.phase === 'error') {
    return { text: state.error?.message ?? 'Search stopped.', tone: 'error' }
  }
  if (state.phase === 'idle') {
    return { text: stats ? `${count(stats.filesTextIndexed, 'file')} ready. Start typing.` : 'Start typing.', tone: 'muted' }
  }
  if (state.phase === 'searching' && resultCount === 0) {
    return { text: 'Searching.', tone: 'muted' }
  }
  if (state.phase === 'done' && resultCount === 0) {
    return { text: 'Nothing matched. Try a word from the file name, or from the text on the page.', tone: 'muted' }
  }

  const took = state.tookMs === null ? '' : ` in ${formatMillis(state.tookMs)}`
  const reading =
    state.phase === 'reading' && state.reading && state.reading.pagesTotal > 0
      ? ` Reading page ${state.reading.pagesRead} of ${state.reading.pagesTotal}.`
      : ''
  return { text: `${count(resultCount, 'page')}${took}.${reading}`, tone: 'muted' }
}
