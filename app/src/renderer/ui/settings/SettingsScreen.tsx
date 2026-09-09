import { useState } from 'react'
import type { ModelsPort, SecretsPort } from '../../application/ports'
import { useSettings } from '../../application/useSettings'
import { blocker, matching, pricePerQuestion, readyFirst, type AnswerProvider } from '../../domain/models'
import { Button } from '../shared/Button'
import { ModelList } from './ModelList'
import { ProviderRow } from './ProviderRow'

interface SettingsScreenProps {
  models: ModelsPort
  secrets: SecretsPort
  onClose: () => void
}

/**
 * Where answers come from: a provider, then one of the models it is offering.
 *
 * The model list is read from the provider rather than written down here, so
 * what is on screen is what that provider has today, at the price it charges
 * today. OpenRouter alone offers 262 of them, which is why the list filters.
 */
export function SettingsScreen({ models, secrets, onClose }: SettingsScreenProps) {
  const settings = useSettings(models, secrets)
  // Cleared when a provider opens rather than in an effect on `showing`,
  // which would write state during a render for no gain.
  const [filter, setFilter] = useState('')

  return (
    <section className="fixed inset-0 z-10 overflow-auto bg-surface" aria-label="Settings">
      <div className="mx-auto w-full max-w-3xl px-8 py-12">
        <header className="flex items-start gap-4">
          <h1 className="flex-1 text-lg text-ink">Settings</h1>
          <Button onClick={onClose}>Close</Button>
        </header>

        <h2 className="mt-10 text-sm text-ink">Answers come from</h2>
        <p className="mt-1 text-xs text-ink-muted">
          Search, the page preview and the heatmap run on this Mac whatever you pick here.
        </p>

        <ul className="mt-4">
          {readyFirst(settings.providers).map((provider) => (
            <li key={provider.id} className="border-t border-border first:border-t-0">
              <ProviderRow
                provider={provider}
                chosen={settings.chosen.provider === provider.id}
                open={settings.showing === provider.id}
                saving={settings.saving}
                blocker={blocker(provider)}
                onOpen={() => {
                  setFilter('')
                  settings.show(settings.showing === provider.id ? '' : provider.id)
                }}
                onSaveKey={(key) => void settings.saveKey(provider.id, key)}
              />
              {settings.showing === provider.id && (
                <ModelList
                  models={matching(settings.models, filter)}
                  total={settings.models.length}
                  loading={settings.loadingModels}
                  filter={filter}
                  onFilter={setFilter}
                  chosenId={settings.chosen.provider === provider.id ? settings.chosen.model : null}
                  onChoose={(modelId) => settings.choose(provider.id, modelId)}
                  price={pricePerQuestion}
                />
              )}
            </li>
          ))}
        </ul>

        {settings.error && (
          <p className="mt-4 text-sm text-status-error" role="alert">
            {settings.error}
          </p>
        )}

        <p className="mt-10 text-xs text-ink-muted">
          Prices come from the provider each time this screen opens, so they are whatever it is charging now.
        </p>
      </div>
    </section>
  )
}

export type { AnswerProvider }
