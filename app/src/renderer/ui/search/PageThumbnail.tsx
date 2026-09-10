import { useEffect, useState } from 'react'
import type { PageImagePort } from '../../application/ports'
import { useInView } from '../shared/useInView'

interface PageThumbnailProps {
  pageId: string
  pageImages: PageImagePort
}

/**
 * The page at postage stamp size, fetched only once its row is near the screen.
 *
 * The frame is drawn before the image arrives, so a list that is still loading
 * has the same shape as one that has finished.
 */
export function PageThumbnail({ pageId, pageImages }: PageThumbnailProps) {
  const { ref, inView } = useInView<HTMLDivElement>()
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!inView) return
    let live = true
    pageImages
      .imageUrl(pageId, 'thumb')
      .then((next) => {
        if (live) setUrl(next)
      })
      .catch(() => undefined)
    return () => {
      live = false
    }
  }, [inView, pageId, pageImages])

  return (
    <div ref={ref} className="h-19 w-14 shrink-0 overflow-hidden rounded-xs bg-border/30">
      {url && (
        <img
          src={url}
          alt=""
          className="h-full w-full object-cover object-top outline-1 -outline-offset-1 outline-ink/10"
        />
      )}
    </div>
  )
}
