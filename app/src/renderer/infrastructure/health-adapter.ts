import type { HealthPort } from '../application/ports'
import type { ModelReadiness, ModelState } from '../domain/model-readiness'
import type { SidecarClient } from './sidecar-client'

interface WireHealth {
  model_loaded: boolean
  model?: {
    state: string
    bytes_done: number
    bytes_total: number
    fraction: number | null
  }
}

const STATES: readonly string[] = ['absent', 'downloading', 'loading', 'ready']

export function createHealthPort(client: SidecarClient): HealthPort {
  return {
    async readiness(): Promise<ModelReadiness> {
      const body = await client.json<WireHealth>('/health')
      const model = body.model
      if (!model) {
        // A sidecar from before this field existed. Reporting it as ready is
        // the quiet answer: the banner stays hidden and nothing else changes.
        return { state: 'ready', bytesDone: 0, bytesTotal: 0, fraction: null }
      }
      return {
        state: (STATES.includes(model.state) ? model.state : 'absent') as ModelState,
        bytesDone: model.bytes_done,
        bytesTotal: model.bytes_total,
        fraction: model.fraction,
      }
    },
  }
}
