export interface RetrievedPage {
  index: number
  pageId: string
  path: string
  pageNo: number
}

export interface Citation {
  index: number
  pageId: string
}

export interface AnswerUsage {
  inputTokens: number
  outputTokens: number
}

/**
 * `retrieving` is before the pages are known, `reading` while the answer
 * streams, `answered` once it has stopped. The panel shows the pages from
 * `reading` onward, because what the answer was allowed to look at is worth
 * seeing before the answer itself.
 */
export type ChatPhase = 'idle' | 'retrieving' | 'reading' | 'answered' | 'error'

export interface ChatState {
  phase: ChatPhase
  askId: string
  question: string
  pages: RetrievedPage[]
  text: string
  citations: Citation[]
  usage: AnswerUsage | null
  costUsd: number | null
  modelId: string | null
  error: { code: string; message: string } | null
}

export const initialChatState: ChatState = {
  phase: 'idle',
  askId: '',
  question: '',
  pages: [],
  text: '',
  citations: [],
  usage: null,
  costUsd: null,
  modelId: null,
  error: null,
}

export type ChatEvent =
  | { type: 'asked'; askId: string; question: string }
  | { type: 'retrieved'; askId: string; pages: RetrievedPage[] }
  | { type: 'token'; askId: string; text: string }
  | { type: 'cited'; askId: string; citation: Citation }
  | { type: 'finished'; askId: string; usage: AnswerUsage; costUsd: number | null; modelId: string }
  | { type: 'failed'; askId: string; error: { code: string; message: string } }
  | { type: 'cleared' }

/**
 * Drives one question from asking to answered.
 *
 * Text is appended, never replaced, because the panel renders what it is
 * given and a stream that rewrites itself reads as a glitch.
 *
 * Every event carries the id of the question that produced it and anything
 * from an older one is dropped. Asking a second question while the first is
 * still streaming is ordinary, and the first answer must not finish writing
 * itself into the second.
 */
export function chatStateReducer(state: ChatState, event: ChatEvent): ChatState {
  if (event.type === 'cleared') return initialChatState
  if (event.type === 'asked') {
    return { ...initialChatState, phase: 'retrieving', askId: event.askId, question: event.question }
  }
  if (event.askId !== state.askId) return state

  switch (event.type) {
    case 'retrieved':
      return { ...state, phase: 'reading', pages: event.pages }
    case 'token':
      return { ...state, text: state.text + event.text }
    case 'cited':
      return { ...state, citations: [...state.citations, event.citation] }
    case 'finished':
      return {
        ...state,
        phase: 'answered',
        usage: event.usage,
        costUsd: event.costUsd,
        modelId: event.modelId,
      }
    case 'failed':
      return { ...state, phase: 'error', error: event.error }
  }
}

/**
 * The pages the answer actually cited, in the order it first cited them.
 *
 * The chips under an answer are what the reader checks it against, so they
 * are the pages that were used rather than the pages that were offered. A
 * page cited twice is one chip.
 */
export function citedPages(state: ChatState): RetrievedPage[] {
  const byId = new Map(state.pages.map((page) => [page.pageId, page]))
  const seen = new Set<string>()
  const cited: RetrievedPage[] = []
  for (const citation of state.citations) {
    const page = byId.get(citation.pageId)
    if (page && !seen.has(page.pageId)) {
      seen.add(page.pageId)
      cited.push(page)
    }
  }
  return cited
}

/** True when the answer said the files do not contain it: an answer with nothing cited. */
export function abstained(state: ChatState): boolean {
  return state.phase === 'answered' && state.citations.length === 0 && state.text.trim() !== ''
}
