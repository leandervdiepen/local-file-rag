import { useId, useState } from 'react'
import type { AnswerProvider } from '../../domain/models'
import { Button } from '../shared/Button'

interface ProviderRowProps {
  provider: AnswerProvider
  chosen: boolean
  open: boolean
  saving: boolean
  blocker: string | null
  onOpen: () => void
  onSaveKey: (key: string) => void
}

/**
 * One place answers can come from.
 *
 * Closed, the row says what state the provider is in. Open, it shows the key
 * field if one is needed, and the model list follows underneath.
 */
export function ProviderRow({ provider, chosen, open, saving, blocker, onOpen, onSaveKey }: ProviderRowProps) {
  const [key, setKey] = useState('')
  const keyFieldId = useId()

  return (
    <div>
      <button
        type="button"
        onClick={onOpen}
        aria-expanded={open}
        className="focus-ring -mx-2 flex w-[calc(100%+1rem)] items-center gap-3 rounded-control px-2 py-2.5 text-left transition-colors hover:bg-border/30"
      >
        <Chevron open={open} />
        <span className="min-w-0 flex-1 truncate text-sm text-ink">{provider.label}</span>
        {chosen && <span className="shrink-0 text-xs text-accent">In use</span>}
        <span className="shrink-0 text-xs text-ink-muted">{stateOf(provider)}</span>
      </button>

      {open && provider.needsKey && (
        <form
          className="flex flex-wrap items-center gap-2 pb-4 pl-7 pt-1"
          onSubmit={(event) => {
            event.preventDefault()
            onSaveKey(key)
            setKey('')
          }}
        >
          <label htmlFor={keyFieldId} className="w-full text-xs text-ink-muted">
            {blocker ?? 'A key is saved. Paste a new one to replace it.'}
          </label>
          <input
            id={keyFieldId}
            type="password"
            value={key}
            onChange={(event) => setKey(event.target.value)}
            autoComplete="off"
            spellCheck={false}
            className="w-72 rounded-control bg-surface px-3 py-1.5 font-mono text-sm text-ink shadow-control focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <Button type="submit" disabled={saving || !key.trim()}>
            {provider.hasKey ? 'Replace key' : 'Save key'}
          </Button>
        </form>
      )}
    </div>
  )
}

function stateOf(provider: AnswerProvider): string {
  if (provider.runsLocally) return 'Runs on this Mac'
  if (!provider.needsKey) return ''
  return provider.hasKey ? 'Key saved' : 'Needs a key'
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      className={`h-4 w-4 shrink-0 text-ink-muted transition-transform ${open ? 'rotate-90' : ''}`}
    >
      <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
