export interface AnswerProvider {
  id: string
  label: string
  needsKey: boolean
  hasKey: boolean
  runsLocally: boolean
}

export interface AnswerModel {
  id: string
  label: string
  provider: string
  /** Null when the provider publishes no price. Never rendered as free. */
  usdPerQuestion: number | null
  /** Null when the provider does not say whether it reads images. */
  seesImages: boolean | null
  contextTokens: number | null
}

/** What a provider needs before it can answer, or null when it is ready. */
export function blocker(provider: AnswerProvider): string | null {
  if (!provider.needsKey || provider.hasKey) return null
  return `Add ${article(provider.label)} ${provider.label} key to use this.`
}

/** Enough for the provider names that exist. A wrong article reads as a typo in the product. */
function article(word: string): string {
  return /^[aeiou]/i.test(word) ? 'an' : 'a'
}

/**
 * What one question costs, as a person choosing between models would compare it.
 *
 * A model nobody priced says so. Printing it as free would invent the one
 * number the reader is charged for.
 */
export function pricePerQuestion(model: AnswerModel): string {
  if (model.usdPerQuestion === null) return 'Price varies'
  if (model.usdPerQuestion <= 0) return 'Free'
  if (model.usdPerQuestion < 0.01) return 'Under $0.01'
  return `$${model.usdPerQuestion.toFixed(2)}`
}

/** Providers that can answer now first, local ones ahead of the rest. */
export function readyFirst(providers: AnswerProvider[]): AnswerProvider[] {
  return [...providers].sort((a, b) => {
    const ready = Number(blocker(a) !== null) - Number(blocker(b) !== null)
    if (ready !== 0) return ready
    const local = Number(b.runsLocally) - Number(a.runsLocally)
    return local !== 0 ? local : a.label.localeCompare(b.label)
  })
}

/** Models whose name or id contains every word typed, so a 262 item list is usable. */
export function matching(models: AnswerModel[], query: string): AnswerModel[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (words.length === 0) return models
  return models.filter((model) => {
    const haystack = `${model.label} ${model.id}`.toLowerCase()
    return words.every((word) => haystack.includes(word))
  })
}
