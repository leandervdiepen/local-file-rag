import { describeModel, type ModelReadiness } from '../../domain/model-readiness'

interface ModelBannerProps {
  readiness: ModelReadiness
}

/**
 * What the app is doing while nothing can be searched yet.
 *
 * First run fetches four and a half gigabytes, and without this the app looks
 * frozen for the whole of it. The bar appears only once the total is known,
 * because one stuck at zero says broken more loudly than no bar at all.
 */
export function ModelBanner({ readiness }: ModelBannerProps) {
  const message = describeModel(readiness)
  if (!message) return null

  return (
    <div role="status" className="border-b border-border py-3">
      <p className="text-sm text-ink">{message}</p>
      {readiness.fraction !== null && (
        <div
          className="mt-2 h-1 w-full overflow-hidden rounded-full bg-border"
          role="progressbar"
          aria-label="Search model download"
          aria-valuenow={Math.round(readiness.fraction * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-200"
            style={{ width: `${readiness.fraction * 100}%` }}
          />
        </div>
      )}
    </div>
  )
}
