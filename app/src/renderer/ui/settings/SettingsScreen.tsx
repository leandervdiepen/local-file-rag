import { useEffect, useState } from 'react'
import type { ModelsPort, SecretsPort } from '../../application/ports'
import { useSettings } from '../../application/useSettings'
import { blocker, matching, pricePerQuestion, readyFirst, type AnswerProvider } from '../../domain/models'
import { OverlayScreen } from '../shared/OverlayScreen'
import { Section } from '../shared/Section'
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
 *
 * Which row is expanded is decided here, and the provider's models are only
 * asked for once it has the key it needs. Asking without one would put a
 * network error under a row whose only problem is a missing key.
 */
export function SettingsScreen({ models, secrets, onClose }: SettingsScreenProps) {
  const settings = useSettings(models, secrets)
  const [expanded, setExpanded] = useState('')
  const [filter, setFilter] = useState('')

  const { providers, showing, show } = settings
  useEffect(() => {
    const provider = providers.find((candidate) => candidate.id === expanded)
    const wanted = provider && blocker(provider) === null ? provider.id : ''
    if (showing !== wanted) show(wanted)
  }, [expanded, providers, showing, show])

  return (
    <OverlayScreen title="Settings" onClose={onClose}>
      <Section
        title="Answers come from"
        hint="Search, the preview and the heatmap run on this Mac whichever you pick. Asking a question sends it, and the pages it draws on, to the provider."
      >
        <ul className="mt-4 divide-y divide-border">
          {readyFirst(providers).map((provider) => {
            const open = expanded === provider.id
            return (
              <li key={provider.id}>
                <ProviderRow
                  provider={provider}
                  chosen={settings.chosen.provider === provider.id}
                  open={open}
                  saving={settings.saving}
                  blocker={blocker(provider)}
                  onOpen={() => {
                    setFilter('')
                    setExpanded(open ? '' : provider.id)
                  }}
                  onSaveKey={(key) => void settings.saveKey(provider.id, key)}
                />
                {open && blocker(provider) === null && (
                  <div className="pb-4 pl-7">
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
                  </div>
                )}
              </li>
            )
          })}
        </ul>

        {settings.error && (
          <p className="mt-4 text-sm text-status-error" role="alert">
            {settings.error}
          </p>
        )}
      </Section>

      <p className="mt-8 text-xs text-ink-muted">Prices are read from the provider each time this screen opens.</p>
    </OverlayScreen>
  )
}

export type { AnswerProvider }
