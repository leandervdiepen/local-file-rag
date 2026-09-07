import { describe, expect, it } from 'vitest'
import { formatBytes, formatMillis } from '../../../src/renderer/domain/format'

describe('formatBytes', () => {
  it('formats zero and negative input as 0 B', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(-5)).toBe('0 B')
  })

  it('formats whole bytes with no decimal', () => {
    expect(formatBytes(512)).toBe('512 B')
  })

  it('formats kilobytes', () => {
    expect(formatBytes(2048)).toBe('2 KB')
  })

  it('formats megabytes matching the measured value in docs/STATUS.md', () => {
    expect(formatBytes(241 * 1024 * 1024)).toBe('241 MB')
  })

  it('drops the decimal once the value reaches double digits', () => {
    expect(formatBytes(10 * 1024 * 1024)).toBe('10 MB')
  })

  it('keeps one decimal below double digits', () => {
    expect(formatBytes(1.5 * 1024 * 1024)).toBe('1.5 MB')
  })
})

describe('formatMillis', () => {
  it('formats zero and negative input as 0 ms', () => {
    expect(formatMillis(0)).toBe('0 ms')
    expect(formatMillis(-1)).toBe('0 ms')
  })

  it('formats sub-second durations as whole milliseconds', () => {
    expect(formatMillis(128)).toBe('128 ms')
  })

  it('formats durations at or above a second in seconds', () => {
    expect(formatMillis(1500)).toBe('1.5 s')
  })

  it('drops the decimal once seconds reach double digits', () => {
    expect(formatMillis(12_000)).toBe('12 s')
  })

  it('drops a trailing .0 for a whole number of seconds', () => {
    expect(formatMillis(2000)).toBe('2 s')
  })
})
