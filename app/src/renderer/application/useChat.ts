import { useCallback, useReducer, useRef } from 'react'
import { chatStateReducer, initialChatState, type ChatState } from '../domain/chat'
import { asSearchError } from '../domain/search-state'
import type { ChatPort } from './ports'

export interface UseChat {
  state: ChatState
  ask: (question: string, modelId: string) => void
  clear: () => void
}

/**
 * Owns one question and the answer streaming back.
 *
 * Asking again abandons the answer in flight rather than queueing behind it.
 * A person who asks a second question has stopped caring about the first, and
 * an answer still being paid for is worth stopping.
 */
export function useChat(port: ChatPort): UseChat {
  const [state, dispatch] = useReducer(chatStateReducer, initialChatState)
  const inFlight = useRef<AbortController | null>(null)
  const issued = useRef(0)

  const ask = useCallback(
    (question: string, modelId: string) => {
      if (!question.trim()) return
      inFlight.current?.abort()

      const controller = new AbortController()
      inFlight.current = controller
      const askId = String((issued.current += 1))
      dispatch({ type: 'asked', askId, question })

      port
        .ask(
          question,
          modelId,
          {
            onRetrieval: (pages) => dispatch({ type: 'retrieved', askId, pages }),
            onToken: (text) => dispatch({ type: 'token', askId, text }),
            onCitation: (citation) => dispatch({ type: 'cited', askId, citation }),
            onDone: (usage, costUsd, model) =>
              dispatch({ type: 'finished', askId, usage, costUsd, modelId: model }),
            onError: (error) => dispatch({ type: 'failed', askId, error }),
          },
          controller.signal,
        )
        .catch((cause: unknown) => {
          if (controller.signal.aborted) return
          dispatch({ type: 'failed', askId, error: asSearchError(cause) })
        })
    },
    [port],
  )

  const clear = useCallback(() => {
    inFlight.current?.abort()
    dispatch({ type: 'cleared' })
  }, [])

  return { state, ask, clear }
}
