import { useState } from 'react'
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

/** One place answers can come from, with the key it needs and a way into its models. */
export function ProviderRow({ provider, chosen, open, saving, blocker, onOpen, onSaveKey }: ProviderRowProps) {
  const [key, setKey] = useState('')

  return (
    <div className="py-3">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpen}
          aria-expanded={open}
          className="flex flex-1 items-baseline gap-2 rounded-control py-1 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <span className="text-sm text-ink">{provider.label}</span>
          {chosen && <span className="text-xs text-accent">in use</span>}
          {provider.runsLocally && <span className="text-xs text-ink-muted">nothing leaves this Mac</span>}
        </button>
        <span className="text-xs text-ink-muted">{open ? 'Hide models' : 'Show models'}</span>
      </div>

      {provider.needsKey && (
        <form
          className="mt-2 flex items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            onSaveKey(key)
            setKey('')
          }}
        >
          <input
            type="password"
            value={key}
            onChange={(event) => setKey(event.target.value)}
            placeholder={provider.hasKey ? 'Key saved' : `${provider.label} API key`}
            aria-label={`${provider.label} API key`}
            autoComplete="off"
            spellCheck={false}
            className="w-72 rounded-control border border-border bg-transparent px-3 py-1.5 font-mono text-xs text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none"
          />
          <Button type="submit" className="px-3 py-1.5 text-xs" disabled={saving || !key.trim()}>
            {provider.hasKey ? 'Replace' : 'Save'}
          </Button>
        </form>
      )}

      {blocker && <p className="mt-2 text-xs text-status-error">{blocker}</p>}
    </div>
  )
}
