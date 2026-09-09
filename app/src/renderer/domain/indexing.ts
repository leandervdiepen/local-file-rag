export interface IndexedFolder {
  id: string
  path: string
  enabled: boolean
  addedAt: string
}

export interface FolderFailure {
  path: string
  reason: string
}

export interface IndexProgress {
  folderId: string
  filesSeen: number
  filesIndexed: number
  filesSkipped: number
  pagesIndexed: number
  pagesEmbedded: number
  currentPath: string
  failures: FolderFailure[]
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
