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
}

// A provider with hundreds of models is unreadable as a list and fine as a
// search, so only this many are drawn until the filter narrows it.
const SHOWN = 40

/** What one provider is offering, filtered because OpenRouter alone offers 262. */
export function ModelList({ models, total, loading, filter, onFilter, chosenId, onChoose, price }: ModelListProps) {
  if (loading) return <p className="pb-3 text-xs text-ink-muted">Asking the provider what it has.</p>
  if (total === 0) return <p className="pb-3 text-xs text-ink-muted">This provider is offering nothing right now.</p>

  const shown = models.slice(0, SHOWN)

  return (
    <div className="pb-4">
      <input
        type="search"
        value={filter}
        onChange={(event) => onFilter(event.target.value)}
        placeholder={`Filter ${total} models`}
        aria-label="Filter models"
        className="w-72 rounded-control border border-border bg-transparent px-3 py-1.5 text-xs text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none"
      />

      <ul className="mt-2 max-h-64 overflow-auto">
        {shown.map((model) => (
          <li key={model.id}>
            <label className="flex cursor-pointer items-baseline gap-3 rounded-control px-2 py-1.5 hover:bg-border/40">
              <input
                type="radio"
                name="answer-model"
                checked={model.id === chosenId}
                onChange={() => onChoose(model.id)}
                className="accent-accent"
              />
              <span className="flex-1 truncate text-xs text-ink" title={model.id}>
                {model.label}
              </span>
              <span className="shrink-0 font-mono text-xs text-ink-muted">{price(model)}</span>
            </label>
          </li>
        ))}
      </ul>

      {models.length > SHOWN && (
        <p className="mt-1 text-xs text-ink-muted">
          {models.length - SHOWN} more. Type to narrow the list.
        </p>
      )}
      {models.length === 0 && <p className="mt-1 text-xs text-ink-muted">Nothing matches that.</p>}
    </div>
  )
}
