const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB'] as const

function trailingDigits(value: number): number {
  return Number.isInteger(value) ? 0 : value < 10 ? 1 : 0
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 1) return '0 B'

  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), BYTE_UNITS.length - 1)
  const value = bytes / 1024 ** exponent
  return `${value.toFixed(trailingDigits(value))} ${BYTE_UNITS[exponent]}`
}

export function formatMillis(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return '0 ms'
  if (ms < 1000) return `${Math.round(ms)} ms`

  const seconds = ms / 1000
  return `${seconds.toFixed(trailingDigits(seconds))} s`
}

/**
 * Writes a path the way the user's shell does.
 *
 * A result list is read by its file names, and an absolute path repeating
 * `/Users/someone` on every row pushes the part that identifies the file off
 * the right edge.
 */
export function shortenHomePath(path: string): string {
  return path.replace(/^\/Users\/[^/]+\//, '~/')
}

export function fileNameOf(path: string): string {
  const separator = path.lastIndexOf('/')
  return separator === -1 ? path : path.slice(separator + 1)
}

/** The folder a file sits in, so a row that already names the file does not name it twice. */
export function directoryOf(path: string): string {
  const separator = path.lastIndexOf('/')
  return separator <= 0 ? '/' : path.slice(0, separator)
}

/** "1 page", "12 pages": one place decides the plural, so no line ever reads "1 files". */
export function count(n: number, singular: string, plural = `${singular}s`): string {
  return `${n.toLocaleString()} ${n === 1 ? singular : plural}`
}
