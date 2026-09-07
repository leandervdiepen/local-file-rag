import { forwardRef, type KeyboardEvent } from 'react'

export interface SearchBoxProps {
  query: string
  listboxId: string
  activeDescendant: string | null
  onQueryChange: (query: string) => void
  onMove: (delta: 1 | -1) => void
  onOpen: () => void
  onReveal: () => void
  onCopyPath: () => void
}

/**
 * The search input, which is also where the result list is driven from.
 *
 * Arrow keys move the selection through `aria-activedescendant` rather than
 * moving focus, so the hand never leaves the box: typing, choosing and opening
 * are one uninterrupted motion.
 */
export const SearchBox = forwardRef<HTMLInputElement, SearchBoxProps>(function SearchBox(
  { query, listboxId, activeDescendant, onQueryChange, onMove, onOpen, onReveal, onCopyPath },
  ref,
) {
  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      onMove(event.key === 'ArrowDown' ? 1 : -1)
      return
    }
    if (event.key === 'Enter') {
      event.preventDefault()
      if (event.metaKey) onReveal()
      else onOpen()
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      onQueryChange('')
      return
    }
    if (event.metaKey && event.shiftKey && event.key.toLowerCase() === 'c') {
      event.preventDefault()
      onCopyPath()
    }
  }

  return (
    <input
      ref={ref}
      type="text"
      role="combobox"
      aria-expanded
      aria-controls={listboxId}
      aria-autocomplete="list"
      {...(activeDescendant ? { 'aria-activedescendant': `result-${activeDescendant}` } : {})}
      autoFocus
      spellCheck={false}
      autoComplete="off"
      value={query}
      placeholder="Search your files"
      onChange={(event) => onQueryChange(event.target.value)}
      onKeyDown={handleKeyDown}
      className="w-full border-b border-border bg-transparent pb-3 text-2xl text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none"
    />
  )
})
