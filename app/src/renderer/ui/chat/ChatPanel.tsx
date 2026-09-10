import { abstained, citedPages, type ChatState, type RetrievedPage } from '../../domain/chat'
import { count } from '../../domain/format'
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
 *
 * Only the phase line is a live region. Streaming text into one would read
 * the whole answer again on every token.
 */
export function ChatPanel({ state, onOpenPage, onClose }: ChatPanelProps) {
  const cited = citedPages(state)

  return (
    <aside
      className="sticky top-0 flex h-screen w-104 shrink-0 flex-col self-start border-l border-border"
      aria-label="Answer"
    >
      <header className="flex items-start gap-3 border-b border-border px-5 py-3">
        <p className="min-w-0 flex-1 py-1.5 text-sm font-medium text-ink">{state.question}</p>
        <Button onClick={onClose}>Close</Button>
      </header>

      <div className="flex-1 overflow-auto px-5 py-4">
        <p role="status" className="text-xs text-ink-muted">
          {state.phase === 'retrieving' && 'Finding pages to read.'}
          {state.pages.length > 0 && `Answering from ${count(state.pages.length, 'page')}.`}
        </p>

        {state.text && <p className="mt-3 whitespace-pre-wrap text-base leading-relaxed text-ink">{state.text}</p>}

        {cited.length > 0 && <CitationChips pages={cited} onOpen={onOpenPage} />}

        {abstained(state) && <p className="mt-4 text-xs text-ink-muted">Nothing cited. The pages it read do not answer this.</p>}

        {state.error && (
          <p role="alert" className="mt-3 text-sm text-status-error">
            {state.error.message}
          </p>
        )}
      </div>

      {state.phase === 'answered' && <AnswerFooter state={state} />}
    </aside>
  )
}
