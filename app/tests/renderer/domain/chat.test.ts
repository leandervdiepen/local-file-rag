import { describe, expect, it } from 'vitest'
import {
  abstained,
  chatStateReducer,
  citedPages,
  initialChatState,
  type ChatState,
  type RetrievedPage,
} from '../../../src/renderer/domain/chat'

const pages: RetrievedPage[] = [
  { index: 1, pageId: 'a:1', path: '/corpus/invoice.pdf', pageNo: 1 },
  { index: 2, pageId: 'b:4', path: '/corpus/deck.pdf', pageNo: 4 },
]

function asked(askId = '1', question = 'what did egress cost'): ChatState {
  return chatStateReducer(initialChatState, { type: 'asked', askId, question })
}

function reading(askId = '1'): ChatState {
  return chatStateReducer(asked(askId), { type: 'retrieved', askId, pages })
}

describe('chatStateReducer', () => {
  it('shows what the answer may look at before any answer arrives', () => {
    const state = reading()

    expect(state.phase).toBe('reading')
    expect(state.pages).toEqual(pages)
    expect(state.text).toBe('')
  })

  it('appends text rather than replacing it', () => {
    let state = reading()
    for (const text of ['Egress was ', '18.4 TB', '.']) {
      state = chatStateReducer(state, { type: 'token', askId: '1', text })
    }

    expect(state.text).toBe('Egress was 18.4 TB.')
  })

  it('collects citations as they arrive', () => {
    let state = reading()
    state = chatStateReducer(state, { type: 'cited', askId: '1', citation: { index: 1, pageId: 'a:1' } })
    state = chatStateReducer(state, { type: 'cited', askId: '1', citation: { index: 2, pageId: 'b:4' } })

    expect(state.citations.map((c) => c.pageId)).toEqual(['a:1', 'b:4'])
  })

  it('carries the cost and the model that produced the answer', () => {
    const state = chatStateReducer(reading(), {
      type: 'finished',
      askId: '1',
      usage: { inputTokens: 9000, outputTokens: 120 },
      costUsd: 0.0072,
      modelId: 'openrouter/free',
    })

    expect(state.phase).toBe('answered')
    expect(state.usage).toEqual({ inputTokens: 9000, outputTokens: 120 })
    expect(state.costUsd).toBe(0.0072)
    expect(state.modelId).toBe('openrouter/free')
  })

  it('drops everything from a question the user has already replaced', () => {
    let state = reading('2')
    state = chatStateReducer(state, { type: 'token', askId: '1', text: 'from the old answer' })
    state = chatStateReducer(state, { type: 'cited', askId: '1', citation: { index: 1, pageId: 'a:1' } })

    expect(state.text).toBe('')
    expect(state.citations).toEqual([])
  })

  it('starts a second question clean rather than on top of the first', () => {
    let state = chatStateReducer(reading(), { type: 'token', askId: '1', text: 'first answer' })
    state = chatStateReducer(state, { type: 'asked', askId: '2', question: 'another' })

    expect(state.text).toBe('')
    expect(state.pages).toEqual([])
    expect(state.question).toBe('another')
  })

  it('surfaces a provider failure as state the panel can render', () => {
    const state = chatStateReducer(reading(), {
      type: 'failed',
      askId: '1',
      error: { code: 'answer_unavailable', message: 'The key was refused.' },
    })

    expect(state.phase).toBe('error')
    expect(state.error?.message).toBe('The key was refused.')
  })
})

describe('citedPages', () => {
  it('lists the pages the answer used, in the order it first used them', () => {
    let state = reading()
    for (const pageId of ['b:4', 'a:1', 'b:4']) {
      state = chatStateReducer(state, { type: 'cited', askId: '1', citation: { index: 1, pageId } })
    }

    expect(citedPages(state).map((page) => page.pageId)).toEqual(['b:4', 'a:1'])
  })

  it('ignores a citation pointing at a page that was never retrieved', () => {
    const state = chatStateReducer(reading(), { type: 'cited', askId: '1', citation: { index: 9, pageId: 'gone:1' } })

    expect(citedPages(state)).toEqual([])
  })
})

describe('abstained', () => {
  it('is true for an answer that cited nothing', () => {
    let state = chatStateReducer(reading(), { type: 'token', askId: '1', text: 'That is not in your files.' })
    state = chatStateReducer(state, {
      type: 'finished',
      askId: '1',
      usage: { inputTokens: 1, outputTokens: 1 },
      costUsd: 0,
      modelId: 'm',
    })

    expect(abstained(state)).toBe(true)
  })

  it('is false while the answer is still streaming, however little has arrived', () => {
    const state = chatStateReducer(reading(), { type: 'token', askId: '1', text: 'Egress' })

    expect(abstained(state)).toBe(false)
  })

  it('is false for an answer that cited something', () => {
    let state = chatStateReducer(reading(), { type: 'token', askId: '1', text: 'Egress was 18.4 TB.' })
    state = chatStateReducer(state, { type: 'cited', askId: '1', citation: { index: 1, pageId: 'a:1' } })
    state = chatStateReducer(state, {
      type: 'finished',
      askId: '1',
      usage: { inputTokens: 1, outputTokens: 1 },
      costUsd: 0,
      modelId: 'm',
    })

    expect(abstained(state)).toBe(false)
  })
})
