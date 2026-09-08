import { describe, expect, it } from 'vitest'
import { mapFor, opacityOf, peakPatch, thresholdAt, type Heatmap } from '../../../src/renderer/domain/heatmap'

const heatmap: Heatmap = {
  rows: 2,
  cols: 2,
  combined: [
    [0, 0.5],
    [0.25, 1],
  ],
  threshold: 0.6,
  thresholdPercentile: 90,
  tokens: [
    { token: 'funnel', values: [[1, 0], [0, 0]] },
    { token: 'chart', values: [[0, 0], [0, 1]] },
  ],
}

describe('mapFor', () => {
  it('draws every token at once by default', () => {
    expect(mapFor(heatmap, { kind: 'combined' })).toBe(heatmap.combined)
  })

  it('draws the one token the user picked', () => {
    expect(mapFor(heatmap, { kind: 'token', index: 1 })).toEqual([[0, 0], [0, 1]])
  })

  it('falls back to the combined map for a token that is not there', () => {
    expect(mapFor(heatmap, { kind: 'token', index: 9 })).toBe(heatmap.combined)
  })
})

describe('thresholdAt', () => {
  it('hides most of the page at the default percentile', () => {
    const values = [Array.from({ length: 10 }, (_, n) => n / 10)]

    // Nearest rank, not interpolated. The sidecar sends the starting cutoff
    // and this only recomputes while a slider is moving, where a fraction of
    // one patch is not visible.
    expect(thresholdAt(values, 90)).toBeCloseTo(0.8)
    expect(values[0]!.filter((v) => v >= thresholdAt(values, 90))).toEqual([0.8, 0.9])
  })

  it('hides nothing at zero and nearly everything at a hundred', () => {
    expect(thresholdAt(heatmap.combined, 0)).toBe(0)
    expect(thresholdAt(heatmap.combined, 100)).toBe(1)
  })

  it('has no cutoff to give for an empty map', () => {
    expect(thresholdAt([], 90)).toBe(0)
  })
})

describe('opacityOf', () => {
  it('draws nothing below the cutoff', () => {
    expect(opacityOf(0.4, 0.6)).toBe(0)
  })

  it('rescales from the cutoff so raising the slider brightens what is left', () => {
    expect(opacityOf(0.6, 0.6)).toBe(0)
    expect(opacityOf(0.8, 0.6)).toBeCloseTo(0.5)
    expect(opacityOf(1, 0.6)).toBe(1)
  })

  it('shows everything that survives when the cutoff is the ceiling', () => {
    expect(opacityOf(1, 1)).toBe(1)
  })
})

describe('peakPatch', () => {
  it('finds the strongest patch', () => {
    expect(peakPatch(heatmap.combined)).toEqual({ row: 1, col: 1 })
  })

  it('picks the first of equals rather than wandering', () => {
    expect(peakPatch([[1, 1], [1, 1]])).toEqual({ row: 0, col: 0 })
  })
})
