import { useEffect, useState } from 'react'
import { modelUnknown, type ModelReadiness } from '../domain/model-readiness'
import type { HealthPort } from './ports'

export const POLL_MS = 1500

/**
 * Watches the model become usable, then stops watching.
 *
 * Polling ends for good once the model has been ready once, because the only
 * thing this is for is the first run, where four and a half gigabytes arrive
 * before anything can be searched. A poll that never stopped would also keep
 * the sidecar looking busy forever, and idle pre-embedding waits for quiet.
 */
export function useModelReadiness(health: HealthPort, pollMs: number = POLL_MS): ModelReadiness {
  const [readiness, setReadiness] = useState<ModelReadiness>(modelUnknown)

  useEffect(() => {
    let live = true
    let timer: ReturnType<typeof setTimeout> | undefined

    async function poll(): Promise<void> {
      try {
        const next = await health.readiness()
        if (!live) return
        setReadiness(next)
        if (next.state === 'ready') return
      } catch {
        // A sidecar that is restarting answers nothing. Keep asking: this is
        // the screen a user stares at, and giving up on it leaves them with
        // no explanation at all.
      }
      if (live) timer = setTimeout(() => void poll(), pollMs)
    }

    void poll()
    return () => {
      live = false
      if (timer) clearTimeout(timer)
    }
  }, [health, pollMs])

  return readiness
}
