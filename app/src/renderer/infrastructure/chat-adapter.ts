import type { ChatHandlers, ChatPort } from '../application/ports'
import type { RetrievedPage } from '../domain/chat'
import type { SidecarClient } from './sidecar-client'

interface WirePage {
  index: number
  page_id: string
  path: string
  page_no: number
}

function toPage(wire: WirePage): RetrievedPage {
  return { index: wire.index, pageId: wire.page_id, path: wire.path, pageNo: wire.page_no }
}

export function createChatPort(client: SidecarClient): ChatPort {
  return {
    ask(question, providerId, modelId, handlers: ChatHandlers, signal) {
      return client.stream(
        '/chat',
        (name, payload) => {
          if (name === 'retrieval') {
            handlers.onRetrieval((payload as { pages: WirePage[] }).pages.map(toPage))
          } else if (name === 'token') {
            handlers.onToken((payload as { text: string }).text)
          } else if (name === 'citation') {
            const body = payload as { index: number; page_id: string }
            handlers.onCitation({ index: body.index, pageId: body.page_id })
          } else if (name === 'done') {
            const body = payload as {
              usage: { input_tokens: number; output_tokens: number }
              cost_usd: number | null
              model_id: string
            }
            handlers.onDone(
              { inputTokens: body.usage.input_tokens, outputTokens: body.usage.output_tokens },
              body.cost_usd,
              body.model_id,
            )
          } else if (name === 'error') {
            handlers.onError(payload as { code: string; message: string })
          }
        },
        signal,
        { method: 'POST', body: { question, provider: providerId, model_id: modelId } },
      )
    },
  }
}
