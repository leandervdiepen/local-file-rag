import type { FileKind } from './search-results'

export interface IndexedFileRow {
  id: string
  path: string
  kind: FileKind
  state: 'text_indexed' | 'skipped'
  skipReason: string | null
  sizeBytes: number
  pageCount: number
  truncatedPages: boolean
}

/**
 * What a skip reason means, said as what the file is.
 *
 * The index screen exists so the user can trust what is missing, which only
 * works if every absence has a reason a person can read and act on. "Failed"
 * is not one of those, so no reason here is a verdict on the file.
 */
const REASONS: Record<string, string> = {
  excluded_path: 'In a folder this app skips, like node_modules or .git',
  unsupported_type: 'Not a kind this version reads. PDF, PNG, JPG, TXT and MD are',
  empty: 'The file has no bytes in it',
  oversized: 'Larger than 200 MB',
  image_too_small: 'Shorter than 300 px on its short side, so it is an icon or a sprite',
  encrypted: 'The PDF needs a password',
  corrupt: 'The file would not open',
}

export function explainSkip(reason: string | null): string {
  if (!reason) return 'Skipped'
  return REASONS[reason] ?? reason.replaceAll('_', ' ')
}

/** Skip reasons ordered by how many files each accounts for, so the biggest cause reads first. */
export function skipsByCount(skipsByReason: Record<string, number>): { reason: string; count: number }[] {
  return Object.entries(skipsByReason)
    .map(([reason, count]) => ({ reason, count }))
    .sort((a, b) => b.count - a.count || a.reason.localeCompare(b.reason))
}
