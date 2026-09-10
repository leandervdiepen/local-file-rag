interface ThresholdSliderProps {
  percentile: number
  onChange: (percentile: number) => void
}

/** How much of the page is lit: the slider moves the cutoff and the number says what is left above it. */
export function ThresholdSlider({ percentile, onChange }: ThresholdSliderProps) {
  const shown = `top ${100 - percentile}%`

  return (
    <label className="flex items-center gap-3 text-xs text-ink-muted">
      <span>Highlight</span>
      <input
        type="range"
        min={50}
        max={99}
        step={1}
        value={percentile}
        aria-valuetext={shown}
        onChange={(event) => onChange(Number(event.target.value))}
        className="focus-ring h-1 w-36 rounded-full accent-accent"
      />
      <span className="w-14 font-mono tabular-nums text-ink">{shown}</span>
    </label>
  )
}
