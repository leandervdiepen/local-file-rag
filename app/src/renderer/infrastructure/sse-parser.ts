export interface ServerSentEvent {
  name: string
  data: string
}

function parseBlock(block: string): ServerSentEvent | null {
  let name = ''
  const dataLines: string[] = []

  for (const line of block.split('\n')) {
    if (line.startsWith(':')) continue
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    const rawValue = colon === -1 ? '' : line.slice(colon + 1)
    const value = rawValue.startsWith(' ') ? rawValue.slice(1) : rawValue

    if (field === 'event') name = value
    else if (field === 'data') dataLines.push(value)
  }

  return dataLines.length === 0 ? null : { name, data: dataLines.join('\n') }
}

/**
 * Reassembles server-sent events from arbitrary chunk boundaries.
 *
 * A chunk is whatever the network handed over, so one event can arrive in
 * three pieces and three events can arrive in one. Everything up to the last
 * blank line is emitted and the remainder is held for the next chunk.
 *
 * The whole buffer is renormalized on each push rather than each chunk,
 * because a CRLF can itself be split, leaving a lone carriage return that a
 * per-chunk replace would never pair up.
 */
export function createSseParser() {
  let buffer = ''

  return {
    push(chunk: string): ServerSentEvent[] {
      buffer = (buffer + chunk).replace(/\r\n/g, '\n')
      const events: ServerSentEvent[] = []

      for (let boundary = buffer.indexOf('\n\n'); boundary !== -1; boundary = buffer.indexOf('\n\n')) {
        const event = parseBlock(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        if (event) events.push(event)
      }

      return events
    },
  }
}
