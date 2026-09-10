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
  excluded_path: 'Inside a folder that is always skipped, like node_modules or .git',
  unsupported_type: 'This version reads PDF, PNG, JPG, TXT and MD',
  empty: 'File is 0 bytes',
  oversized: 'Over the 200 MB limit',
  image_too_small: 'Image is under 300 px on its short side',
  encrypted: 'PDF is password protected',
  corrupt: 'File would not open',
}

/** The same reasons as a label short enough to sit beside a count. */
const LABELS: Record<string, string> = {
  excluded_path: 'in a skipped folder',
  unsupported_type: 'of a type this version does not read',
  empty: 'empty',
  oversized: 'over 200 MB',
  image_too_small: 'under 300 px',
  encrypted: 'password protected',
  corrupt: 'would not open',
}

export function explainSkip(reason: string | null): string {
  if (!reason) return 'Skipped'
  return REASONS[reason] ?? reason.replaceAll('_', ' ')
}

export function labelSkip(reason: string): string {
  return LABELS[reason] ?? reason.replaceAll('_', ' ')
}

/** Skip reasons ordered by how many files each accounts for, so the biggest cause reads first. */
export function skipsByCount(skipsByReason: Record<string, number>): { reason: string; count: number }[] {
  return Object.entries(skipsByReason)
    .map(([reason, count]) => ({ reason, count }))
    .sort((a, b) => b.count - a.count || a.reason.localeCompare(b.reason))
}
