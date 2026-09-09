import { abstained, citedPages, type ChatState, type RetrievedPage } from '../../domain/chat'
import { Button } from '../shared/Button'
import { AnswerFooter } from './AnswerFooter'
import { CitationChips } from './CitationChips'

interface ChatPanelProps {
  state: ChatState
  onOpenPage: (page: RetrievedPage) => void
  onClose: () => void
}

/**
 * The answer, its citations and what it cost.
 *
 * The pages the answer was allowed to read are counted before the answer
 * arrives, so a reader can see what it looked at while it is still writing.
 * The chips underneath are only the pages it actually cited, because those
 * are the ones worth checking.
 */
export function ChatPanel({ state, onOpenPage, onClose }: ChatPanelProps) {
  const cited = citedPages(state)

  return (
    <aside className="flex h-full w-[26rem] shrink-0 flex-col border-l border-border" aria-label="Answer">
      <header className="flex items-start gap-3 border-b border-border px-5 py-4">
        <p className="min-w-0 flex-1 text-sm text-ink">{state.question}</p>
        <Button onClick={onClose}>Close</Button>
      </header>

      <div className="flex-1 overflow-auto px-5 py-4" aria-live="polite">
        {state.phase === 'retrieving' && <p className="text-sm text-ink-muted">Reading your pages.</p>}

        {state.pages.length > 0 && (
          <p className="mb-4 text-xs text-ink-muted">
            Answering from {state.pages.length} {state.pages.length === 1 ? 'page' : 'pages'}.
          </p>
        )}

        {state.text && <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{state.text}</p>}

        {cited.length > 0 && <CitationChips pages={cited} onOpen={onOpenPage} />}

        {abstained(state) && (
          <p className="mt-4 text-xs text-ink-muted">
            Nothing is cited here, so this is the model saying the pages do not answer it.
          </p>
        )}

        {state.error && <p className="text-sm text-status-error">{state.error.message}</p>}
      </div>

      {state.phase === 'answered' && <AnswerFooter state={state} />}
    </aside>
  )
}
