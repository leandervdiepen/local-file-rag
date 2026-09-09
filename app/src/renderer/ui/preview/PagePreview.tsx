import { useEffect, useMemo, useState } from 'react'
import type { HeatmapPort, PageImagePort } from '../../application/ports'
import { usePageExplanation } from '../../application/usePageExplanation'
import { shortenHomePath } from '../../domain/format'
import { mapFor, thresholdAt, type HeatmapView } from '../../domain/heatmap'
import type { PageHit } from '../../domain/search-results'
import { Button } from '../shared/Button'
import { HeatmapOverlay } from './HeatmapOverlay'
import { ThresholdSlider } from './ThresholdSlider'
import { TokenPicker } from './TokenPicker'

interface PagePreviewProps {
  hit: PageHit
  query: string
  pageImages: PageImagePort
  heatmaps: HeatmapPort
  onClose: () => void
}

/**
 * One page, full size, with the reason it matched drawn over it.
 *
 * The page is shown as soon as its image arrives and stays whatever the
 * explanation does. An overlay that failed to load leaves a page the user can
 * still read, which is worth more than an error where the page would be.
 */
export function PagePreview({ hit, query, pageImages, heatmaps, onClose }: PagePreviewProps) {
  const [url, setUrl] = useState<string | null>(null)
  const [view, setView] = useState<HeatmapView>({ kind: 'combined' })
  const [percentile, setPercentile] = useState<number | null>(null)
  const { heatmap, error } = usePageExplanation(heatmaps, hit.pageId, query)

  useEffect(() => {
    let live = true
    pageImages
      .imageUrl(hit.pageId, 'full')
      .then((next) => {
        if (live) setUrl(next)
      })
      .catch(() => undefined)
    return () => {
      live = false
    }
  }, [hit.pageId, pageImages])

  const values = heatmap ? mapFor(heatmap, view) : null
  const showing = percentile ?? heatmap?.thresholdPercentile ?? 90
  const threshold = useMemo(() => (values ? thresholdAt(values, showing) : 0), [values, showing])

  return (
    <section className="fixed inset-0 z-10 flex flex-col bg-surface" aria-label={`Page ${hit.pageNo}`}>
      <header className="flex items-center gap-4 border-b border-border px-6 py-3">
        <div className="min-w-0 flex-1">
          <p className="truncate font-mono text-sm text-ink">{shortenHomePath(hit.path)}</p>
          <p className="font-mono text-xs text-ink-muted">Page {hit.pageNo}</p>
        </div>
        {heatmap && <TokenPicker heatmap={heatmap} view={view} onChange={setView} />}
        {heatmap && <ThresholdSlider percentile={showing} onChange={setPercentile} />}
        <Button onClick={onClose}>Close</Button>
      </header>

      <div className="flex flex-1 items-start justify-center overflow-auto p-6">
        <div className="relative">
          {url && <img src={url} alt="" className="max-h-full w-auto rounded-control border border-border" />}
          {url && values && <HeatmapOverlay values={values} threshold={threshold} />}
        </div>
      </div>

      {error && <p className="border-t border-border px-6 py-2 text-xs text-ink-muted">{error.message}</p>}
    </section>
  )
}
