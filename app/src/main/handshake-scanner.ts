const READY_LINE = /^READY (\d+)$/

export interface HandshakeScannerCallbacks {
  onReady: (port: number) => void
  onProtocolViolation: (line: string) => void
}

/** `READY <port>` arrives once. Anything else on stdout, before or after it, is a protocol violation. */
export function createHandshakeScanner({ onReady, onProtocolViolation }: HandshakeScannerCallbacks) {
  let buffer = ''
  let readyReceived = false

  return (chunk: Buffer): void => {
    buffer += chunk.toString('utf8')
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.length === 0) continue

      if (readyReceived) {
        onProtocolViolation(`unexpected stdout after ready: ${trimmed}`)
        continue
      }

      const match = READY_LINE.exec(trimmed)
      if (match?.[1]) {
        readyReceived = true
        onReady(Number(match[1]))
      } else {
        onProtocolViolation(`protocol violation on stdout: ${trimmed}`)
      }
    }
  }
}
