import { useEffect, useMemo, useRef } from 'react'
import type { NativeActionsPort, PageImagePort, SearchPort } from '../../application/ports'
import { useResultSelection } from '../../application/useResultSelection'
import { useSearch } from '../../application/useSearch'
import type { IndexProgress, IndexStats } from '../../domain/indexing'
import { flattenGroups, groupByFile } from '../../domain/search-results'
import { IndexingBanner } from './IndexingBanner'
import { ResultList } from './ResultList'
import { SearchBox } from './SearchBox'
import { SearchStatus } from './SearchStatus'

const LISTBOX_ID = 'search-results'

interface SearchScreenProps {
  search: SearchPort
  pageImages: PageImagePort
  nativeActions: NativeActionsPort
  progress: IndexProgress | null
  stats: IndexStats | null
}

export function SearchScreen({ search, pageImages, nativeActions, progress, stats }: SearchScreenProps) {
  const { state, query, setQuery } = useSearch(search)
  const input = useRef<HTMLInputElement>(null)

  const groups = useMemo(() => groupByFile(state.hits), [state.hits])
  const ordered = useMemo(() => flattenGroups(groups), [groups])
  const orderedIds = useMemo(() => ordered.map((hit) => hit.pageId), [ordered])
  const selection = useResultSelection(orderedIds)
  const selectedPath = ordered.find((hit) => hit.pageId === selection.selected)?.path ?? null

  // The product is a search box, so a keystroke anywhere on the window belongs
  // to it. Modifier combinations are left alone: those are shortcuts, not text.
  useEffect(() => {
    function focusOnTyping(event: KeyboardEvent): void {
      if (event.metaKey || event.ctrlKey || event.altKey || event.key.length !== 1) return
      if (document.activeElement instanceof HTMLInputElement) return
      input.current?.focus()
    }
    window.addEventListener('keydown', focusOnTyping)
    return () => window.removeEventListener('keydown', focusOnTyping)
  }, [])

  const actions = useMemo(
    () => ({
      open: (path: string) => void nativeActions.openPath(path),
      reveal: (path: string) => void nativeActions.revealInFinder(path),
      copyPath: (path: string) => void nativeActions.copyPath(path),
    }),
    [nativeActions],
  )

  const onSelected = (act: (path: string) => void) => () => {
    if (selectedPath) act(selectedPath)
  }

  return (
    <main className="mx-auto min-h-screen w-full max-w-3xl px-8 py-12">
      <SearchBox
        ref={input}
        query={query}
        listboxId={LISTBOX_ID}
        activeDescendant={selection.selected}
        onQueryChange={setQuery}
        onMove={selection.move}
        onOpen={onSelected(actions.open)}
        onReveal={onSelected(actions.reveal)}
        onCopyPath={onSelected(actions.copyPath)}
      />

      {progress && !progress.done && <IndexingBanner progress={progress} />}
      <SearchStatus state={state} stats={stats} resultCount={ordered.length} />

      <ResultList
        id={LISTBOX_ID}
        groups={groups}
        selectedPageId={selection.selected}
        pageImages={pageImages}
        actions={actions}
        onSelect={selection.select}
      />
    </main>
  )
}
