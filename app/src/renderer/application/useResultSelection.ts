import { useCallback, useState } from 'react'
import { moveSelection, retainSelection } from '../domain/selection'

export interface UseResultSelection {
  selected: string | null
  select: (pageId: string) => void
  move: (delta: 1 | -1) => void
}

/**
 * Keeps one row selected as results change under it, and moves it on request.
 *
 * The selection is validated while rendering rather than corrected afterwards.
 * A row that a new result set no longer contains simply stops being selected,
 * so there is never a frame showing a highlight on a row that is not there.
 */
export function useResultSelection(orderedIds: readonly string[]): UseResultSelection {
  const [requested, setRequested] = useState<string | null>(null)
  const selected = retainSelection(requested, orderedIds)

  return {
    selected,
    select: useCallback((pageId: string) => setRequested(pageId), []),
    move: useCallback(
      (delta: 1 | -1) => setRequested(moveSelection(selected, orderedIds, delta)),
      [selected, orderedIds],
    ),
  }
}
