import { describe, expect, it } from 'vitest'
import {
  blocker,
  matching,
  pricePerQuestion,
  readyFirst,
  type AnswerModel,
  type AnswerProvider,
} from '../../../src/renderer/domain/models'

function model(over: Partial<AnswerModel>): AnswerModel {
  return {
    id: 'p/m',
    label: 'A model',
    provider: 'p',
    usdPerQuestion: 0.05,
    seesImages: true,
    contextTokens: 100_000,
    ...over,
  }
}

function provider(over: Partial<AnswerProvider>): AnswerProvider {
  return { id: 'p', label: 'Provider', needsKey: true, hasKey: false, runsLocally: false, ...over }
}

describe('what stops a model answering', () => {
  it('names the provider whose key is missing', () => {
    expect(blocker(provider({ label: 'OpenRouter' }))).toBe('Add an OpenRouter key to use this.')
  })

  it('gets the article right, because a wrong one reads as a typo in the product', () => {
    expect(blocker(provider({ label: 'Google Gemini' }))).toBe('Add a Google Gemini key to use this.')
    expect(blocker(provider({ label: 'Anthropic' }))).toBe('Add an Anthropic key to use this.')
  })

  it('is nothing once the key is there', () => {
    expect(blocker(provider({ hasKey: true }))).toBeNull()
  })

  it('is nothing for a model that runs on this Mac', () => {
    expect(blocker(provider({ needsKey: false, runsLocally: true }))).toBeNull()
  })
})

describe('what one question costs', () => {
  it('says free rather than zero dollars', () => {
    expect(pricePerQuestion(model({ usdPerQuestion: 0 }))).toBe('Free')
  })

  it('does not round a fraction of a cent down to nothing', () => {
    expect(pricePerQuestion(model({ usdPerQuestion: 0.004 }))).toBe('Under $0.01')
  })

  it('gives a comparable number for a model that charges', () => {
    expect(pricePerQuestion(model({ usdPerQuestion: 0.123 }))).toBe('$0.12')
  })

  it('says a price was never checked rather than calling it free', () => {
    expect(pricePerQuestion(model({ usdPerQuestion: null }))).toBe('Price varies')
  })
})

describe('the order providers are offered in', () => {
  it('puts the ones that can answer now first', () => {
    const ordered = readyFirst([provider({ id: 'locked' }), provider({ id: 'ready', hasKey: true })])

    expect(ordered.map((p) => p.id)).toEqual(['ready', 'locked'])
  })

  it('puts a provider that runs on this Mac ahead of the rest', () => {
    const ordered = readyFirst([
      provider({ id: 'hosted', hasKey: true }),
      provider({ id: 'local', needsKey: false, runsLocally: true }),
    ])

    expect(ordered.map((p) => p.id)).toEqual(['local', 'hosted'])
  })

  it('leaves the list it was given alone', () => {
    const given = [provider({ id: 'a' }), provider({ id: 'b', hasKey: true })]

    readyFirst(given)

    expect(given.map((p) => p.id)).toEqual(['a', 'b'])
  })
})

describe('filtering a provider with hundreds of models', () => {
  it('keeps only the models carrying every word typed', () => {
    const found = matching(
      [model({ id: 'a', label: 'Gemini 3.8 Flash' }), model({ id: 'b', label: 'Claude Opus' })],
      'gemini flash',
    )

    expect(found.map((m) => m.id)).toEqual(['a'])
  })

  it('searches the id as well as the name, since that is what people paste', () => {
    const found = matching([model({ id: 'deepseek/v4-vision', label: 'Something Else' })], 'deepseek')

    expect(found.map((m) => m.id)).toEqual(['deepseek/v4-vision'])
  })

  it('returns everything for an empty filter', () => {
    const all = [model({ id: 'a' }), model({ id: 'b' })]

    expect(matching(all, '   ')).toHaveLength(2)
  })
})
