import { afterEach, describe, expect, it, vi } from 'vitest'
import { createIndexedFolders } from '../../src/main/indexed-folders'

afterEach(() => vi.unstubAllGlobals())

function stubFetch(handler: (url: string, init: RequestInit) => Promise<Response> | Response) {
  const calls: { url: string; init: RequestInit }[] = []
  vi.stubGlobal('fetch', (url: string, init: RequestInit) => {
    calls.push({ url, init })
    return Promise.resolve(handler(url, init))
  })
  return calls
}

function foldersResponse(folders: { path: string; enabled: boolean }[]): Response {
  return { ok: true, json: () => Promise.resolve({ folders }) } as Response
}

describe('createIndexedFolders', () => {
  it('allows nothing while the sidecar has not finished starting', async () => {
    const calls = stubFetch(() => foldersResponse([{ path: '/Users/me/Docs', enabled: true }]))
    const roots = createIndexedFolders('t', () => null)

    expect(await roots()).toEqual([])
    expect(calls).toHaveLength(0)
  })

  it('returns the paths of the enabled folders', async () => {
    stubFetch(() =>
      foldersResponse([
        { path: '/Users/me/Docs', enabled: true },
        { path: '/Users/me/Archive', enabled: false },
      ]),
    )
    const roots = createIndexedFolders('t', () => 'http://127.0.0.1:5000')

    expect(await roots()).toEqual(['/Users/me/Docs'])
  })

  it('authenticates as the sidecar requires', async () => {
    const calls = stubFetch(() => foldersResponse([]))
    await createIndexedFolders('secret-token', () => 'http://127.0.0.1:5000')()

    expect(calls[0]?.url).toBe('http://127.0.0.1:5000/folders')
    expect(calls[0]?.init.headers).toEqual({ Authorization: 'Bearer secret-token' })
  })

  it('allows nothing when the sidecar refuses the request', async () => {
    stubFetch(() => ({ ok: false, json: () => Promise.resolve({}) }) as Response)
    const roots = createIndexedFolders('t', () => 'http://127.0.0.1:5000')

    expect(await roots()).toEqual([])
  })

  it('allows nothing when the sidecar is unreachable', async () => {
    stubFetch(() => {
      throw new TypeError('fetch failed')
    })
    const roots = createIndexedFolders('t', () => 'http://127.0.0.1:5000')

    expect(await roots()).toEqual([])
  })
})
