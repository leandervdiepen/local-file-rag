import { describe, expect, it } from 'vitest'
import { contentSecurityPolicy } from '../../src/main/window'

const DEV_URL = 'http://localhost:5173'

function directive(policy: string, name: string): string {
  return policy.split('; ').find((part) => part.startsWith(`${name} `)) ?? ''
}

describe('the content security policy', () => {
  it('allows no inline script in a packaged build', () => {
    // Inline style is a separate directive and stays allowed: Tailwind writes
    // one. What must never ship is an inline script.
    const scriptSrc = directive(contentSecurityPolicy(undefined), 'script-src')

    expect(scriptSrc).toBe("script-src 'self'")
  })

  it('lets a page image reach an img element, which only works as a blob url', () => {
    expect(directive(contentSecurityPolicy(undefined), 'img-src')).toContain('blob:')
  })

  it('reaches nothing but itself and the loopback sidecar in a packaged build', () => {
    const policy = contentSecurityPolicy(undefined)

    expect(policy).toContain("connect-src 'self' http://127.0.0.1:*")
    expect(policy).toContain("default-src 'self'")
  })

  it('lets the dev server install fast refresh, which needs an inline script', () => {
    const policy = contentSecurityPolicy(DEV_URL)

    expect(policy).toContain("script-src 'self' 'unsafe-inline' http://localhost:5173")
  })

  it('lets the dev server talk over its websocket for hot reload', () => {
    const policy = contentSecurityPolicy(DEV_URL)

    expect(policy).toContain('ws://localhost:5173')
  })

  it('relaxes for the dev origin it was given and no other', () => {
    const policy = contentSecurityPolicy(DEV_URL)

    expect(policy).not.toContain('*://')
    expect(policy).not.toContain("script-src 'self' 'unsafe-inline' *")
  })
})
