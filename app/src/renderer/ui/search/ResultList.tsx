import type { PageImagePort } from '../../application/ports'
import { shortenHomePath } from '../../domain/format'
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

export function ResultList({ id, groups, selectedPageId, pageImages, actions, onSelect }: ResultListProps) {
  return (
    <ul id={id} role="listbox" aria-label="Results" className="pb-16">
      {groups.map((group) => (
        <li key={group.fileId} role="presentation" className="mt-8 first:mt-0">
          <div className="px-3">
            <p className="truncate font-mono text-sm text-ink">{group.fileName}</p>
            <p className="truncate text-xs text-ink-muted" title={group.path}>
              {shortenHomePath(group.path)}
            </p>
          </div>

          <ul role="presentation" className="mt-2">
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
