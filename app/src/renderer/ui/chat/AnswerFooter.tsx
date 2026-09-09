import type { ChatState } from '../../domain/chat'

interface AnswerFooterProps {
  state: ChatState
}

/** What the answer cost, in tokens and in money. Zero is written as free, not as 0.0000 dollars. */
export function AnswerFooter({ state }: AnswerFooterProps) {
  const { usage, costUsd, modelId } = state
  if (!usage) return null

  const total = usage.inputTokens + usage.outputTokens
  const price = costUsd === null || costUsd === 0 ? 'free' : `$${costUsd.toFixed(4)}`

  return (
    <footer className="border-t border-border px-5 py-3 text-xs text-ink-muted">
      <span className="font-mono tabular-nums">{total.toLocaleString()} tokens</span>
      <span aria-hidden> · </span>
      <span className="font-mono tabular-nums">{price}</span>
      {modelId && (
        <>
          <span aria-hidden> · </span>
          <span className="font-mono">{modelId}</span>
        </>
      )}
    </footer>
  )
}
