import { describe, expect, it } from 'vitest'
import { explainSkip, skipsByCount } from '../../../src/renderer/domain/skip-reasons'

describe('explainSkip', () => {
  it('says what the file is rather than that something failed', () => {
    expect(explainSkip('image_too_small')).toContain('300 px')
    expect(explainSkip('encrypted')).toContain('password')
    expect(explainSkip('oversized')).toContain('200 MB')
  })

  it('never says failed, for any reason it knows', () => {
    for (const reason of ['excluded_path', 'unsupported_type', 'empty', 'oversized', 'image_too_small', 'encrypted', 'corrupt']) {
      expect(explainSkip(reason).toLowerCase()).not.toContain('fail')
    }
  })

  it('makes a reason it has never seen readable rather than dropping it', () => {
    expect(explainSkip('some_new_reason')).toBe('some new reason')
  })

  it('has something to say for a file with no reason recorded', () => {
    expect(explainSkip(null)).toBe('Skipped')
  })
})

describe('skipsByCount', () => {
  it('puts the biggest cause first, because that is the one worth acting on', () => {
    const ordered = skipsByCount({ encrypted: 5, image_too_small: 60, empty: 15 })

    expect(ordered.map((row) => row.reason)).toEqual(['image_too_small', 'empty', 'encrypted'])
  })

  it('breaks a tie by name so the list does not reshuffle between renders', () => {
    const ordered = skipsByCount({ zebra: 3, apple: 3 })

    expect(ordered.map((row) => row.reason)).toEqual(['apple', 'zebra'])
  })

  it('has nothing to show when nothing was skipped', () => {
    expect(skipsByCount({})).toEqual([])
  })
})
