interface ThresholdSliderProps {
  percentile: number
  onChange: (percentile: number) => void
}

export function ThresholdSlider({ percentile, onChange }: ThresholdSliderProps) {
  return (
    <label className="flex items-center gap-3 text-xs text-ink-muted">
      Highlight
      <input
        type="range"
        min={50}
        max={99}
        step={1}
        value={percentile}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-1 w-40 accent-accent"
      />
      <span className="w-16 font-mono tabular-nums">top {100 - percentile}%</span>
    </label>
  )
}
