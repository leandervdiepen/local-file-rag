import { useEffect, useState } from 'react'
import type { PageImagePort } from '../../application/ports'
import { useInView } from '../shared/useInView'

interface PageThumbnailProps {
  pageId: string
  pageImages: PageImagePort
}

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
    <div ref={ref} className="h-20 w-16 shrink-0 overflow-hidden rounded-control border border-border bg-surface">
      {url && <img src={url} alt="" className="h-full w-full object-cover object-top" />}
    </div>
  )
}
