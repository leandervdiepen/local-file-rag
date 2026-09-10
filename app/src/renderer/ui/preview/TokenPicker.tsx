import type { Heatmap, HeatmapView } from '../../domain/heatmap'

interface TokenPickerProps {
  heatmap: Heatmap
  view: HeatmapView
  onChange: (view: HeatmapView) => void
}

const CHIP = 'focus-ring rounded-control px-2 py-1 text-xs transition-colors'

/** Which words the overlay shows: all of them, or one word of the query on its own. */
export function TokenPicker({ heatmap, view, onChange }: TokenPickerProps) {
  const chip = (active: boolean) =>
    `${CHIP} ${active ? 'bg-accent/15 text-ink' : 'text-ink-muted hover:bg-border/40 hover:text-ink'}`

  return (
    <div className="flex flex-wrap items-center gap-0.5" role="group" aria-label="Which words to show">
      <button
        type="button"
        aria-pressed={view.kind === 'combined'}
        className={chip(view.kind === 'combined')}
        onClick={() => onChange({ kind: 'combined' })}
      >
        All words
      </button>
      {heatmap.tokens.map((token, index) => {
        const active = view.kind === 'token' && view.index === index
        return (
          <button
            key={`${token.token}-${index}`}
            type="button"
            aria-pressed={active}
            className={chip(active)}
            onClick={() => onChange({ kind: 'token', index })}
          >
            {token.token}
          </button>
        )
      })}
    </div>
  )
}
