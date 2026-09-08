export interface TokenMap {
  token: string
  values: number[][]
}

export interface Heatmap {
  rows: number
  cols: number
  combined: number[][]
  threshold: number
  thresholdPercentile: number
  tokens: TokenMap[]
}

/** Which map the overlay draws: everything at once, or one token the user picked. */
export type HeatmapView = { kind: 'combined' } | { kind: 'token'; index: number }

export function mapFor(heatmap: Heatmap, view: HeatmapView): number[][] {
  if (view.kind === 'combined') return heatmap.combined
  return heatmap.tokens[view.index]?.values ?? heatmap.combined
}

/**
 * The cutoff below which a patch is drawn as nothing.
 *
 * A similarity map is never zero anywhere, so drawing all of it tints the
 * whole page instead of pointing at something. The slider moves this, and the
 * sidecar's own default is the starting position.
 */
export function thresholdAt(values: number[][], percentile: number): number {
  const flat = values.flat().sort((a, b) => a - b)
  if (flat.length === 0) return 0
  const index = Math.min(flat.length - 1, Math.max(0, Math.round((percentile / 100) * (flat.length - 1))))
  return flat[index] ?? 0
}

/**
 * One patch's opacity, given the cutoff.
 *
 * Rescaled from the cutoff rather than from zero, so moving the slider up
 * makes the remaining patches brighter instead of leaving a dim wash that
 * fades uniformly. Below the cutoff nothing is drawn at all.
 */
export function opacityOf(value: number, threshold: number, ceiling = 1): number {
  if (value < threshold) return 0
  const span = ceiling - threshold
  return span <= 0 ? 1 : Math.min(1, (value - threshold) / span)
}

/** The strongest patch, which is where a reader's eye should be sent first. */
export function peakPatch(values: number[][]): { row: number; col: number } {
  let best = { row: 0, col: 0 }
  let bestValue = -Infinity
  values.forEach((row, rowIndex) =>
    row.forEach((value, colIndex) => {
      if (value > bestValue) {
        bestValue = value
        best = { row: rowIndex, col: colIndex }
      }
    }),
  )
  return best
}
