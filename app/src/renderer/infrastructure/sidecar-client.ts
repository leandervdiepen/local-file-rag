import type { SearchError } from '../domain/search-state'
import { createSseParser } from './sse-parser'

export interface SidecarConnection {
  baseUrl: string
  token: string
}

interface WireError {
  error?: { code?: string; message?: string }
}

const UNREACHABLE: SearchError = {
  code: 'sidecar_unreachable',
  message: 'The local engine is not responding. Restart it from the engine panel.',
}

async function toSearchError(response: Response): Promise<SearchError> {
  const body = (await response.json().catch(() => ({}))) as WireError
  return {
    code: body.error?.code ?? 'http_error',
    message: body.error?.message ?? 'Something went wrong on this device.',
  }
}

/**
 * The one place a bearer token is attached and a wire error becomes a value.
 *
 * Every failure leaves here as a `SearchError` with a code the UI switches on,
 * including the ones `fetch` raises rather than returns: a refused connection
 * and a 500 are the same event to someone looking at the window.
 */
export function createSidecarClient(connection: SidecarConnection) {
  const headers = { Authorization: `Bearer ${connection.token}` }
  const url = (path: string) => `${connection.baseUrl}${path}`

  async function request(path: string, init: RequestInit = {}): Promise<Response> {
    let response: Response
    try {
      response = await fetch(url(path), { ...init, headers: { ...headers, ...init.headers } })
    } catch {
      throw UNREACHABLE
    }
    if (!response.ok) throw await toSearchError(response)
    return response
  }

  return {
    async json<T>(path: string, init?: RequestInit): Promise<T> {
      return (await request(path, init)).json() as Promise<T>
    },

    async blob(path: string): Promise<Blob> {
      return (await request(path)).blob()
    },

    async send(path: string, method: string, body?: unknown): Promise<void> {
      await request(path, {
        method,
        ...(body === undefined ? {} : { body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } }),
      })
    },

    /** Reads a named-event stream to its end, or until `signal` aborts it. */
    async stream(
      path: string,
      onEvent: (name: string, payload: unknown) => void,
      signal: AbortSignal,
      send?: { method: string; body: unknown },
    ): Promise<void> {
      const response = await request(path, {
        signal,
        ...(send
          ? { method: send.method, body: JSON.stringify(send.body), headers: { 'Content-Type': 'application/json' } }
          : {}),
      })
      if (!response.body) throw UNREACHABLE

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      const parser = createSseParser()

      try {
        for (;;) {
          const { done, value } = await reader.read()
          if (done) return
          for (const event of parser.push(decoder.decode(value, { stream: true }))) {
            onEvent(event.name, JSON.parse(event.data))
          }
        }
      } finally {
        reader.cancel().catch(() => undefined)
      }
    },
  }
}

export type SidecarClient = ReturnType<typeof createSidecarClient>
