import type { PageImagePort } from '../../application/ports'
import { directoryOf, shortenHomePath } from '../../domain/format'
import type { FileGroup } from '../../domain/search-results'
import { ResultRow, type ResultActions } from './ResultRow'

interface ResultListProps {
  id: string
  groups: FileGroup[]
  selectedPageId: string | null
  pageImages: PageImagePort
  actions: ResultActions
  onSelect: (pageId: string) => void
}

/**
 * Results grouped by file, the file named once above its pages.
 *
 * The list is pulled out by the row padding so text lines up with the search
 * box above it, and only the selection highlight reaches into the margin.
 */
export function ResultList({ id, groups, selectedPageId, pageImages, actions, onSelect }: ResultListProps) {
  return (
    <ul id={id} role="listbox" aria-label="Results" className="-mx-3 pb-16">
      {groups.map((group) => (
        <li key={group.fileId} role="presentation" className="mt-7 first:mt-1">
          <div className="px-3">
            <p className="truncate font-mono text-sm font-medium text-ink">{group.fileName}</p>
            <p className="truncate font-mono text-xs text-ink-muted" title={group.path}>
              {shortenHomePath(directoryOf(group.path))}
            </p>
          </div>

          <ul role="presentation" className="mt-1.5">
            {group.hits.map((hit) => (
              <ResultRow
                key={hit.pageId}
                hit={hit}
                selected={hit.pageId === selectedPageId}
                pageImages={pageImages}
                actions={actions}
                onSelect={onSelect}
              />
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}
