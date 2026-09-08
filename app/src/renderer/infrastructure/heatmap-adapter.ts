import type { HeatmapPort } from '../application/ports'
import type { SidecarClient } from './sidecar-client'

interface WireHeatmap {
  rows: number
  cols: number
  combined: number[][]
  threshold: number
  threshold_percentile: number
  tokens: { token: string; values: number[][] }[]
}

export function createHeatmapPort(client: SidecarClient): HeatmapPort {
  return {
    async explain(pageId, query, signal) {
      const path = `/pages/${encodeURIComponent(pageId)}/heatmap?q=${encodeURIComponent(query)}`
      const wire = await client.json<WireHeatmap>(path, { signal })
      return {
        rows: wire.rows,
        cols: wire.cols,
        combined: wire.combined,
        threshold: wire.threshold,
        thresholdPercentile: wire.threshold_percentile,
        tokens: wire.tokens,
      }
    },
  }
}
