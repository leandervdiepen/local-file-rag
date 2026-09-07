/**
 * Moves the selection down or up a flat list of ids.
 *
 * Nothing selected and a step down selects the first row, and a step up
 * selects the last, so the arrow keys work the moment results land without
 * the user first having to click one.
 *
 * Selection stops at both ends rather than wrapping. Wrapping in a list that
 * scrolls sends the eye somewhere it did not ask to go.
 */
export function moveSelection(current: string | null, ordered: readonly string[], delta: 1 | -1): string | null {
  const at = (index: number): string | null => ordered[index] ?? null

  if (ordered.length === 0) return null

  const index = current === null ? -1 : ordered.indexOf(current)
  if (index === -1) return at(delta === 1 ? 0 : ordered.length - 1)

  return at(Math.min(Math.max(index + delta, 0), ordered.length - 1))
}

/** Keeps a selection only while the thing it points at is still on screen. */
export function retainSelection(current: string | null, ordered: readonly string[]): string | null {
  return current !== null && ordered.includes(current) ? current : null
}
