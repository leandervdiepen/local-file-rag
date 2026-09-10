import { useEffect, useMemo, useRef, useState } from 'react'
import type {
  ChatPort,
  HeatmapPort,
  NativeActionsPort,
  PageImagePort,
  SearchPort,
} from '../../application/ports'
import { useChat } from '../../application/useChat'
import { useResultSelection } from '../../application/useResultSelection'
import { useSearch } from '../../application/useSearch'
import type { Chosen } from '../../application/useSettings'
import type { IndexProgress, IndexStats } from '../../domain/indexing'
import type { ModelReadiness } from '../../domain/model-readiness'
import { flattenGroups, groupByFile } from '../../domain/search-results'
import { ChatPanel } from '../chat/ChatPanel'
import { PagePreview } from '../preview/PagePreview'
import { FolderProblems } from '../index/FolderProblems'
import { QuietButton } from '../shared/QuietButton'
import { IndexingBanner } from './IndexingBanner'
import { ModelBanner } from './ModelBanner'
import { ResultList } from './ResultList'
import { SearchBox } from './SearchBox'
import { SearchStatus } from './SearchStatus'

const LISTBOX_ID = 'search-results'

interface SearchScreenProps {
  search: SearchPort
  pageImages: PageImagePort
  heatmaps: HeatmapPort
  chat: ChatPort
  answerWith: Chosen
  nativeActions: NativeActionsPort
  progress: IndexProgress | null
  modelReadiness: ModelReadiness
  stats: IndexStats | null
  onShowIndex: () => void
  onShowSettings: () => void
}

export function SearchScreen({
  search,
  pageImages,
  heatmaps,
  chat,
  answerWith,
  nativeActions,
  progress,
  modelReadiness,
  stats,
  onShowIndex,
  onShowSettings,
}: SearchScreenProps) {
  const { state, query, setQuery } = useSearch(search)
  const input = useRef<HTMLInputElement>(null)
  const [previewing, setPreviewing] = useState(false)
  const [asking, setAsking] = useState(false)
  const [citedPageId, setCitedPageId] = useState<string | null>(null)
  const answer = useChat(chat)

  const groups = useMemo(() => groupByFile(state.hits), [state.hits])
  const ordered = useMemo(() => flattenGroups(groups), [groups])
  const orderedIds = useMemo(() => ordered.map((hit) => hit.pageId), [ordered])
  const selection = useResultSelection(orderedIds)
  const selected = ordered.find((hit) => hit.pageId === selection.selected) ?? null
  const selectedPath = selected?.path ?? null
  const cited = citedPageId ? (ordered.find((hit) => hit.pageId === citedPageId) ?? null) : null
  const preview = cited ?? (previewing && selected ? selected : null)

  // Brought back by the global shortcut, the caret goes where the user is
  // already typing, with what is there selected so the next key replaces it.
  useEffect(() => {
    const bridge = window.bridge
    if (!bridge?.onWindowShown) return
    return bridge.onWindowShown(() => {
      input.current?.focus()
      input.current?.select()
    })
  }, [])

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
    <main className="flex min-h-screen">
      <div className="mx-auto w-full max-w-3xl px-8 py-12">
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
          onTogglePreview={() => setPreviewing((open) => !open && selected !== null)}
          onAsk={() => {
            setAsking(true)
            answer.ask(query, answerWith.provider, answerWith.model)
          }}
        />

        <ModelBanner readiness={modelReadiness} />
        {progress && !progress.done && <IndexingBanner progress={progress} />}
        {progress && <FolderProblems failures={progress.failures} />}
        <div className="flex items-baseline justify-between gap-4">
          <SearchStatus state={state} stats={stats} resultCount={ordered.length} />
          <div className="-mr-2 flex shrink-0 items-baseline gap-1">
            <QuietButton onClick={onShowIndex}>Index</QuietButton>
            <QuietButton onClick={onShowSettings}>Settings</QuietButton>
          </div>
        </div>

        <ResultList
          id={LISTBOX_ID}
          groups={groups}
          selectedPageId={selection.selected}
          pageImages={pageImages}
          actions={actions}
          onSelect={selection.select}
        />

        {preview && (
          <PagePreview
            hit={preview}
            query={query}
            pageImages={pageImages}
            heatmaps={heatmaps}
            onClose={() => {
              setPreviewing(false)
              setCitedPageId(null)
              input.current?.focus()
            }}
          />
        )}
      </div>

      {asking && (
        <ChatPanel
          state={answer.state}
          onOpenPage={(page) => setCitedPageId(page.pageId)}
          onClose={() => {
            setAsking(false)
            answer.clear()
            input.current?.focus()
          }}
        />
      )}
    </main>
  )
}
