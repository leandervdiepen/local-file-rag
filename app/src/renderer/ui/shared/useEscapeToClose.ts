import { useEffect } from 'react'

/**
 * Escape closes whatever this is mounted in.
 *
 * Listened for in the capture phase so the search box underneath, which
 * clears the query on Escape, does not also hear it. One press dismisses the
 * page on top; the next one reaches the box.
 */
export function useEscapeToClose(onClose: () => void): void {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      onClose()
    }
    window.addEventListener('keydown', onKeyDown, true)
    return () => window.removeEventListener('keydown', onKeyDown, true)
  }, [onClose])
}
