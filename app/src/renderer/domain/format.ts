// Pure formatters. No imports: numbers in, strings out.

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
