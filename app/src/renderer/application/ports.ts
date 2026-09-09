import type { IndexedFolder, IndexProgress, IndexStats } from '../domain/indexing'
import type { IndexedFileRow } from '../domain/skip-reasons'
import type { AnswerUsage, Citation, RetrievedPage } from '../domain/chat'
import type { Heatmap } from '../domain/heatmap'
import type { PageHit } from '../domain/search-results'
import type { SidecarState } from '../domain/sidecar-state'

export interface SidecarConnectionInfo {
  baseUrl: string
  token: string
}

export interface SidecarPort {
  getConnectionInfo: () => SidecarConnectionInfo
  subscribe: (onState: (state: SidecarState) => void) => () => void
  restart: () => Promise<void>
}

export interface OpenPathResult {
  ok: boolean
  error?: string
}

export interface NativeActionsPort {
  openPath: (path: string) => Promise<OpenPathResult>
  revealInFinder: (path: string) => Promise<void>
  copyPath: (path: string) => Promise<void>
  pickFolder: () => Promise<string | null>
}

export interface SecretsPort {
  setAnthropicKey: (key: string) => Promise<void>
  hasAnthropicKey: () => Promise<boolean>
}

export interface SearchHandlers {
  onCandidates: (hits: PageHit[], tookMs: number) => void
  onProgress: (pagesRead: number, pagesTotal: number) => void
  onResults: (hits: PageHit[], tookMs: number) => void
  onFinished: () => void
}

export interface SearchPort {
  /** Streams one search. Resolves when the stream ends, rejects with a `SearchError`. */
  search: (query: string, handlers: SearchHandlers, signal: AbortSignal) => Promise<void>
}

export interface FoldersPort {
  list: () => Promise<IndexedFolder[]>
  add: (path: string) => Promise<IndexedFolder>
  remove: (id: string) => Promise<void>
}

export interface FilePage {
  files: IndexedFileRow[]
  nextCursor: string | null
}

export interface IndexPort {
  rescan: () => Promise<void>
  stats: () => Promise<IndexStats>
  /** One page of files in a state, `cursor` of null starting at the beginning. */
  files: (state: 'text_indexed' | 'skipped', cursor: string | null) => Promise<FilePage>
  /** Streams crawl progress. Resolves when the job ends, so no job is an immediate resolve. */
  watchProgress: (onProgress: (progress: IndexProgress) => void, signal: AbortSignal) => Promise<void>
}

export type PageImageSize = 'thumb' | 'full'

export interface PageImagePort {
  /**
   * A URL an `<img>` can use for a rendered page.
   *
   * An `img` element cannot carry an Authorization header, and the sidecar
   * accepts the token nowhere else, so the bytes are fetched here and handed
   * over as an object URL.
   */
  imageUrl: (pageId: string, size: PageImageSize) => Promise<string>
}

export interface HeatmapPort {
  /** The grid explaining why this page matched this query. Rejects with a `SearchError`. */
  explain: (pageId: string, query: string, signal: AbortSignal) => Promise<Heatmap>
}

export interface ChatHandlers {
  onRetrieval: (pages: RetrievedPage[]) => void
  onToken: (text: string) => void
  onCitation: (citation: Citation) => void
  onDone: (usage: AnswerUsage, costUsd: number, modelId: string) => void
  onError: (error: { code: string; message: string }) => void
}

export interface ChatPort {
  /** Streams one answer. Resolves when the stream ends, rejects with a `SearchError`. */
  ask: (question: string, modelId: string, handlers: ChatHandlers, signal: AbortSignal) => Promise<void>
}
