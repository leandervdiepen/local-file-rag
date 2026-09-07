import { describe, expect, it } from 'vitest'
import { createSseParser } from '../../../src/renderer/infrastructure/sse-parser'

describe('createSseParser', () => {
  it('reads one whole event', () => {
    const parser = createSseParser()

    expect(parser.push('event: candidates\ndata: {"hits":[]}\n\n')).toEqual([
      { name: 'candidates', data: '{"hits":[]}' },
    ])
  })

  it('holds a partial event until the rest arrives', () => {
    const parser = createSseParser()

    expect(parser.push('event: candi')).toEqual([])
    expect(parser.push('dates\ndata: {"hits"')).toEqual([])
    expect(parser.push(':[]}\n\n')).toEqual([{ name: 'candidates', data: '{"hits":[]}' }])
  })

  it('reads several events out of one chunk', () => {
    const parser = createSseParser()
    const events = parser.push('event: a\ndata: 1\n\nevent: b\ndata: 2\n\n')

    expect(events.map((event) => event.name)).toEqual(['a', 'b'])
  })

  it('pairs a CRLF that was split across two chunks', () => {
    const parser = createSseParser()

    expect(parser.push('event: a\r\ndata: 1\r')).toEqual([])
    expect(parser.push('\n\r\n')).toEqual([{ name: 'a', data: '1' }])
  })

  it('joins the data of a multi-line event', () => {
    const parser = createSseParser()

    expect(parser.push('event: a\ndata: one\ndata: two\n\n')).toEqual([{ name: 'a', data: 'one\ntwo' }])
  })

  it('skips comment lines and events carrying no data', () => {
    const parser = createSseParser()

    expect(parser.push(': keep-alive\n\nevent: a\n\n')).toEqual([])
  })
})
