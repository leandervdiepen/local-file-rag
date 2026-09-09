export interface IndexedFolder {
  id: string
  path: string
  enabled: boolean
  addedAt: string
}

export interface IndexProgress {
  folderId: string
  filesSeen: number
  filesIndexed: number
  filesSkipped: number
  pagesIndexed: number
  pagesEmbedded: number
  currentPath: string
  done: boolean
}

export interface IndexStats {
  filesScanned: number
  filesTextIndexed: number
  filesSkipped: number
  pagesTotal: number
  pagesEmbedded: number
  bytesOnDisk: number
  skipsByReason: Record<string, number>
}

export const noProgress: IndexProgress = {
  folderId: '',
  filesSeen: 0,
  filesIndexed: 0,
  filesSkipped: 0,
  pagesIndexed: 0,
  pagesEmbedded: 0,
  currentPath: '',
  done: false,
}
