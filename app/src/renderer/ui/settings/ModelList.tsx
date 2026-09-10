import type { AnswerModel } from '../../domain/models'

interface ModelListProps {
  models: AnswerModel[]
  total: number
  loading: boolean
  filter: string
  onFilter: (value: string) => void
  chosenId: string | null
  onChoose: (modelId: string) => void
  price: (model: AnswerModel) => string
  /** True when the provider could not be reached, so this stays quiet and lets the error speak. */
  failed: boolean
}

// A provider with hundreds of models is unreadable as a list and fine as a
// search, so only this many are drawn until the filter narrows it.
const SHOWN = 40

/** What one provider is offering, filtered because OpenRouter alone offers 262. */
export function ModelList({
  models,
  total,
  loading,
  filter,
  onFilter,
  chosenId,
  onChoose,
  price,
  failed,
}: ModelListProps) {
  if (loading) {
    return (
      <p role="status" className="text-xs text-ink-muted">
        Loading models.
      </p>
    )
  }
  // Nothing to say here when the fetch failed: the error above already says
  // what happened, and two messages read as two problems.
  if (total === 0) return failed ? null : <p className="text-xs text-ink-muted">This provider is offering nothing.</p>

  const shown = models.slice(0, SHOWN)

  return (
    <div>
      <input
        type="search"
        value={filter}
        onChange={(event) => onFilter(event.target.value)}
        placeholder={`Filter ${total} models`}
        aria-label="Filter models"
        className="w-72 rounded-control bg-surface px-3 py-1.5 text-sm text-ink shadow-control placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-accent"
      />

      <ul className="-mx-2 mt-2 max-h-72 overflow-auto">
        {shown.map((model) => (
          <li key={model.id}>
            <label className="flex cursor-default items-center gap-3 rounded-control px-2 py-1.5 hover:bg-border/30">
              <input
                type="radio"
                name="answer-model"
                checked={model.id === chosenId}
                onChange={() => onChoose(model.id)}
                className="focus-ring accent-accent"
              />
              <span className="min-w-0 flex-1 truncate text-sm text-ink" title={model.id}>
                {model.label}
              </span>
              <span className="shrink-0 font-mono text-xs text-ink-muted">{price(model)}</span>
            </label>
          </li>
        ))}
      </ul>

      {models.length > SHOWN && (
        <p className="mt-2 text-xs text-ink-muted">{models.length - SHOWN} more. Type to narrow the list.</p>
      )}
      {models.length === 0 && <p className="mt-2 text-xs text-ink-muted">No models match "{filter}".</p>}
    </div>
  )
}
