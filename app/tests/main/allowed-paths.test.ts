import { describe, expect, it } from 'vitest'
import { isPathAllowed } from '../../src/main/allowed-paths'

describe('isPathAllowed', () => {
  it('rejects everything when the allowlist is empty', () => {
    expect(isPathAllowed('/Users/me/Documents/file.pdf', [])).toBe(false)
  })

  it('allows a path inside an allowed root', () => {
    expect(isPathAllowed('/Users/me/Documents/file.pdf', ['/Users/me/Documents'])).toBe(true)
  })

  it('allows the root itself', () => {
    expect(isPathAllowed('/Users/me/Documents', ['/Users/me/Documents'])).toBe(true)
  })

  it('rejects a sibling whose name merely shares a prefix', () => {
    expect(isPathAllowed('/Users/me/Documents-evil/file.pdf', ['/Users/me/Documents'])).toBe(false)
  })

  it('rejects a path outside every allowed root', () => {
    expect(isPathAllowed('/etc/passwd', ['/Users/me/Documents'])).toBe(false)
  })

  it('resolves .. before checking, so traversal cannot escape', () => {
    expect(isPathAllowed('/Users/me/Documents/../../etc/passwd', ['/Users/me/Documents'])).toBe(false)
  })
})
