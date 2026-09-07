import { useEffect, useRef, useState } from 'react'

/**
 * Reports whether an element has come near the viewport, once.
 *
 * Stage 1 returns up to 300 candidates and each one has a thumbnail the
 * sidecar has to render, so loading them all when results land would spend a
 * second of work on rows nobody scrolls to. It never flips back to false: a
 * page image already fetched costs nothing to keep showing.
 */
export function useInView<T extends Element>(rootMargin = '200px') {
  const ref = useRef<T | null>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element || inView) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) setInView(true)
      },
      { rootMargin },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [inView, rootMargin])

  return { ref, inView }
}
