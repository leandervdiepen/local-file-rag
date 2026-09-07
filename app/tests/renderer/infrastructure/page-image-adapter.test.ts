import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPageImagePort } from '../../../src/renderer/infrastructure/page-image-adapter'
import type { SidecarClient } from '../../../src/renderer/infrastructure/sidecar-client'

const revoked: string[] = []

beforeEach(() => {
  revoked.length = 0
  let issued = 0
  vi.stubGlobal('URL', {
    createObjectURL: () => `blob:${(issued += 1)}`,
    revokeObjectURL: (url: string) => revoked.push(url),
  })
})

function clientRequesting(paths: string[]): SidecarClient {
  return {
    blob: async (path: string) => {
      paths.push(path)
      return new Blob(['png'])
    },
  } as unknown as SidecarClient
}

describe('createPageImagePort', () => {
  it('fetches a page image once and serves the same URL after that', async () => {
    const paths: string[] = []
    const port = createPageImagePort(clientRequesting(paths))

    const first = await port.imageUrl('a:1', 'thumb')
    const second = await port.imageUrl('a:1', 'thumb')

    expect(first).toBe(second)
    expect(paths).toHaveLength(1)
  })

  it('shares one request between two rows asking at the same time', async () => {
    const paths: string[] = []
    const port = createPageImagePort(clientRequesting(paths))

    await Promise.all([port.imageUrl('a:1', 'thumb'), port.imageUrl('a:1', 'thumb')])

    expect(paths).toHaveLength(1)
  })

  it('treats the two sizes of one page as two images', async () => {
    const paths: string[] = []
    const port = createPageImagePort(clientRequesting(paths))

    await port.imageUrl('a:1', 'thumb')
    await port.imageUrl('a:1', 'full')

    expect(paths).toEqual(['/pages/a%3A1/image?size=thumb', '/pages/a%3A1/image?size=full'])
  })

  it('evicts the least recently used image, not the oldest one fetched', async () => {
    const port = createPageImagePort(clientRequesting([]), 2)

    const first = await port.imageUrl('a:1', 'thumb')
    const second = await port.imageUrl('b:1', 'thumb')
    await port.imageUrl('a:1', 'thumb')
    await port.imageUrl('c:1', 'thumb')

    expect(revoked).toEqual([second])
    expect(revoked).not.toContain(first)
  })

  it('retries after a failure instead of caching it', async () => {
    let attempts = 0
    const client = {
      blob: async () => {
        attempts += 1
        if (attempts === 1) throw { code: 'not_found', message: 'gone' }
        return new Blob(['png'])
      },
    } as unknown as SidecarClient
    const port = createPageImagePort(client)

    await expect(port.imageUrl('a:1', 'thumb')).rejects.toMatchObject({ code: 'not_found' })
    await expect(port.imageUrl('a:1', 'thumb')).resolves.toMatch(/^blob:/)
    expect(attempts).toBe(2)
  })
})
