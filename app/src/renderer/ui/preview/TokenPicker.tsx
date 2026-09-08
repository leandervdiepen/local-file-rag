import type { Heatmap, HeatmapView } from '../../domain/heatmap'

interface TokenPickerProps {
  heatmap: Heatmap
  view: HeatmapView
  onChange: (view: HeatmapView) => void
}

const CHIP = 'rounded-control px-2 py-1 text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent'

export function TokenPicker({ heatmap, view, onChange }: TokenPickerProps) {
  const chip = (active: boolean) => `${CHIP} ${active ? 'bg-accent/15 text-ink' : 'text-ink-muted hover:bg-border/50'}`

  return (
    <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Which words to show">
      <button type="button" className={chip(view.kind === 'combined')} onClick={() => onChange({ kind: 'combined' })}>
        All words
      </button>
      {heatmap.tokens.map((token, index) => (
        <button
          key={`${token.token}-${index}`}
          type="button"
          className={chip(view.kind === 'token' && view.index === index)}
          onClick={() => onChange({ kind: 'token', index })}
        >
          {token.token}
        </button>
      ))}
    </div>
  )
}
