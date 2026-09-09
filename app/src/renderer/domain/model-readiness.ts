export type ModelState = 'absent' | 'downloading' | 'loading' | 'ready'

export interface ModelReadiness {
  state: ModelState
  bytesDone: number
  bytesTotal: number
  /** Null while the total is unknown, so the UI shows a spinner rather than a bar stuck at zero. */
  fraction: number | null
}

export const modelUnknown: ModelReadiness = {
  state: 'absent',
  bytesDone: 0,
  bytesTotal: 0,
  fraction: null,
}

/**
 * What to say while the model is being made ready, or null when there is nothing to say.
 *
 * Silent when the model is ready and when it is merely absent: absent is the
 * resting state of a machine nobody has searched on yet, and announcing it
 * would put a warning on an app that is working correctly.
 */
export function describeModel(readiness: ModelReadiness): string | null {
  if (readiness.state === 'loading') return 'Starting the search model.'
  if (readiness.state !== 'downloading') return null
  if (readiness.bytesTotal <= 0) return 'Getting the search model. This happens once.'
  return `Getting the search model. ${gigabytes(readiness.bytesDone)} of ${gigabytes(readiness.bytesTotal)} GB.`
}

function gigabytes(bytes: number): string {
  return (bytes / 1024 ** 3).toFixed(1)
}
