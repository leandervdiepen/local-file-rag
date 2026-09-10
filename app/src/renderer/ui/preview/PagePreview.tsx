import { useEffect, useMemo, useState } from 'react'
import type { HeatmapPort, PageImagePort } from '../../application/ports'
import { usePageExplanation } from '../../application/usePageExplanation'
import { directoryOf, fileNameOf, shortenHomePath } from '../../domain/format'
import { mapFor, thresholdAt, type HeatmapView } from '../../domain/heatmap'
import type { PageHit } from '../../domain/search-results'
import { Button } from '../shared/Button'
import { useEscapeToClose } from '../shared/useEscapeToClose'
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
 * One page, fitted to the window, with the reason it matched drawn over it.
 *
 * The page is shown as soon as its image arrives and stays whatever the
 * explanation does. An overlay that failed to load leaves a page the user can
 * still read, which is worth more than an error where the page would be.
 *
 * The header keeps its height while the explanation loads, so the page does
 * not jump when the controls for it arrive.
 */
export function PagePreview({ hit, query, pageImages, heatmaps, onClose }: PagePreviewProps) {
  const [url, setUrl] = useState<string | null>(null)
  const [view, setView] = useState<HeatmapView>({ kind: 'combined' })
  const [percentile, setPercentile] = useState<number | null>(null)
  const { heatmap, error, loading } = usePageExplanation(heatmaps, hit.pageId, query)
  useEscapeToClose(onClose)

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
  const fileName = fileNameOf(hit.path)

  return (
    <section className="fixed inset-0 z-10 flex flex-col bg-surface" aria-label={`${fileName}, page ${hit.pageNo}`}>
      <header className="border-b border-border px-6 py-3">
        <div className="flex items-center gap-4">
          <div className="min-w-0 flex-1">
            <p className="truncate font-mono text-sm font-medium text-ink">
              {fileName}
              {hit.kind === 'pdf' && <span className="ml-2 font-normal text-ink-muted">Page {hit.pageNo}</span>}
            </p>
            <p className="truncate font-mono text-xs text-ink-muted" title={hit.path}>
              {shortenHomePath(directoryOf(hit.path))}
            </p>
          </div>
          <Button onClick={onClose}>Close</Button>
        </div>

        <div className="mt-3 flex min-h-6 flex-wrap items-center justify-between gap-x-6 gap-y-2">
          {heatmap && <TokenPicker heatmap={heatmap} view={view} onChange={setView} />}
          {heatmap && <ThresholdSlider percentile={showing} onChange={setPercentile} />}
          {loading && (
            <p role="status" className="text-xs text-ink-muted">
              Finding what matched.
            </p>
          )}
          {error && (
            <p role="status" className="text-xs text-ink-muted">
              {error.message}
            </p>
          )}
        </div>
      </header>

      <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden p-6">
        {url && (
          <div className="relative overflow-hidden rounded-xs shadow-control">
            <img src={url} alt="" className="block max-h-[calc(100vh-9.5rem)] max-w-full" />
            {values && <HeatmapOverlay values={values} threshold={threshold} />}
          </div>
        )}
      </div>
    </section>
  )
}
