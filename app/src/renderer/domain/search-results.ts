export type FileKind = 'pdf' | 'image' | 'text' | 'unknown'

export interface PageHit {
  pageId: string
  fileId: string
  path: string
  pageNo: number
  kind: FileKind
  score: number
  stage: string
  snippet: string
}

export interface FileGroup {
  fileId: string
  path: string
  fileName: string
  kind: FileKind
  hits: PageHit[]
}

function fileNameOf(path: string): string {
  const separator = path.lastIndexOf('/')
  return separator === -1 ? path : path.slice(separator + 1)
}

/**
 * Groups hits by their file, keeping the ranking the sidecar decided.
 *
 * A group's place in the list is the place of its best hit, so the strongest
 * match is still the first thing on screen. Inside a group the pages run in
 * page order rather than by score, because someone reading three pages of one
 * document is reading a document, and a document that jumps 7, 2, 5 is harder
 * to scan than one whose best page is second.
 */
export function groupByFile(hits: readonly PageHit[]): FileGroup[] {
  const groups = new Map<string, FileGroup>()

  for (const hit of hits) {
    const existing = groups.get(hit.fileId)
    if (existing) {
      existing.hits.push(hit)
      continue
    }
    groups.set(hit.fileId, {
      fileId: hit.fileId,
      path: hit.path,
      fileName: fileNameOf(hit.path),
      kind: hit.kind,
      hits: [hit],
    })
  }

  const ordered = [...groups.values()]
  for (const group of ordered) group.hits.sort((a, b) => a.pageNo - b.pageNo)
  return ordered
}

/** Every hit in the order it is rendered, which is the order the arrow keys walk. */
export function flattenGroups(groups: readonly FileGroup[]): PageHit[] {
  return groups.flatMap((group) => group.hits)
}
