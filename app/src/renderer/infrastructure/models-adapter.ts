import type { ModelsPort } from '../application/ports'
import type { AnswerModel, AnswerProvider } from '../domain/models'
import type { SidecarClient } from './sidecar-client'

interface WireProvider {
  id: string
  label: string
  needs_key: boolean
  has_key: boolean
  runs_locally: boolean
}

interface WireModel {
  id: string
  label: string
  provider: string
  usd_per_question: number | null
  sees_images: boolean | null
  context_tokens: number | null
}

function toProvider(wire: WireProvider): AnswerProvider {
  return {
    id: wire.id,
    label: wire.label,
    needsKey: wire.needs_key,
    hasKey: wire.has_key,
    runsLocally: wire.runs_locally,
  }
}

function toModel(wire: WireModel): AnswerModel {
  return {
    id: wire.id,
    label: wire.label,
    provider: wire.provider,
    usdPerQuestion: wire.usd_per_question,
    seesImages: wire.sees_images,
    contextTokens: wire.context_tokens,
  }
}

export function createModelsPort(client: SidecarClient): ModelsPort {
  return {
    async providers() {
      const body = await client.json<{ providers: WireProvider[] }>('/providers')
      return body.providers.map(toProvider)
    },

    async modelsFor(providerId) {
      const path = `/providers/${encodeURIComponent(providerId)}/models`
      const body = await client.json<{ models: WireModel[] }>(path)
      return body.models.map(toModel)
    },
  }
}
