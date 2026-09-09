import { useCallback, useEffect, useState } from 'react'
import { DEFAULT_MODEL_ID, DEFAULT_PROVIDER_ID } from '../domain/models-default'
import type { AnswerModel, AnswerProvider } from '../domain/models'
import type { ModelsPort, SecretsPort } from './ports'

const CHOSEN = 'local-file-rag.answer-model'

export interface Chosen {
  provider: string
  model: string
}

export interface UseSettings {
  providers: AnswerProvider[]
  models: AnswerModel[]
  /** Which provider's list is on screen, which is not yet a choice of model. */
  showing: string
  show: (providerId: string) => void
  loadingModels: boolean
  chosen: Chosen
  choose: (provider: string, model: string) => void
  saveKey: (provider: string, key: string) => Promise<void>
  saving: boolean
  error: string | null
}

/**
 * Which provider and model answer, and which providers have a key.
 *
 * The choice is remembered in this window rather than in the sidecar, because
 * it belongs to the person at the keyboard and not to the index. What a
 * provider offers is asked of the provider, so opening its list is a network
 * call and can fail on its own without breaking the rest of the screen.
 */
export function useSettings(modelsPort: ModelsPort, secrets: SecretsPort): UseSettings {
  const [providers, setProviders] = useState<AnswerProvider[]>([])
  const [models, setModels] = useState<AnswerModel[]>([])
  const [showing, setShowing] = useState('')
  const [loadingModels, setLoadingModels] = useState(false)
  const [chosen, setChosen] = useState<Chosen>(remembered)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadProviders = useCallback(async () => {
    setProviders(await modelsPort.providers())
  }, [modelsPort])

  useEffect(() => {
    let live = true
    modelsPort
      .providers()
      .then((found) => live && setProviders(found))
      .catch(() => live && setError('The local engine did not answer with its providers.'))
    return () => {
      live = false
    }
  }, [modelsPort])

  const show = useCallback(
    (providerId: string) => {
      setShowing(providerId)
      setModels([])
      setError(null)
      if (!providerId) return
      setLoadingModels(true)
      modelsPort
        .modelsFor(providerId)
        .then(setModels)
        .catch((cause: unknown) => setError(messageFrom(cause)))
        .finally(() => setLoadingModels(false))
    },
    [modelsPort],
  )

  const choose = useCallback((provider: string, model: string) => {
    const next = { provider, model }
    setChosen(next)
    remember(next)
  }, [])

  const saveKey = useCallback(
    async (provider: string, key: string) => {
      setSaving(true)
      setError(null)
      try {
        await secrets.setKey(provider, key)
        await loadProviders()
        if (showing === provider) show(provider)
      } catch (cause: unknown) {
        setError(messageFrom(cause))
      } finally {
        setSaving(false)
      }
    },
    [secrets, loadProviders, show, showing],
  )

  return { providers, models, showing, show, loadingModels, chosen, choose, saveKey, saving, error }
}

function messageFrom(cause: unknown): string {
  return cause instanceof Error && cause.message ? cause.message : 'That did not work.'
}

function remembered(): Chosen {
  const fallback = { provider: DEFAULT_PROVIDER_ID, model: DEFAULT_MODEL_ID }
  try {
    const stored = window.localStorage.getItem(CHOSEN)
    if (!stored) return fallback
    const parsed: unknown = JSON.parse(stored)
    if (typeof parsed !== 'object' || parsed === null) return fallback
    const { provider, model } = parsed as Partial<Chosen>
    return typeof provider === 'string' && typeof model === 'string' ? { provider, model } : fallback
  } catch {
    return fallback
  }
}

function remember(chosen: Chosen): void {
  try {
    window.localStorage.setItem(CHOSEN, JSON.stringify(chosen))
  } catch {
    // A window with storage blocked still works, it just forgets the choice
    // when it closes. Losing a preference is not worth failing over.
  }
}
