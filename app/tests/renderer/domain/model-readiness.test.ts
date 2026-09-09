import { describe, expect, it } from 'vitest'
import { describeModel, type ModelReadiness } from '../../../src/renderer/domain/model-readiness'

function readiness(over: Partial<ModelReadiness>): ModelReadiness {
  return { state: 'absent', bytesDone: 0, bytesTotal: 0, fraction: null, ...over }
}

describe('what to say while the model is being made ready', () => {
  it('says nothing when the model is ready', () => {
    expect(describeModel(readiness({ state: 'ready' }))).toBeNull()
  })

  it('says nothing on a machine nobody has searched on yet', () => {
    // Absent is the resting state, and warning about it would put an error on
    // an app that is working correctly.
    expect(describeModel(readiness({ state: 'absent' }))).toBeNull()
  })

  it('says the download happens once, before the size is known', () => {
    expect(describeModel(readiness({ state: 'downloading' }))).toBe('Getting the search model. This happens once.')
  })

  it('counts in gigabytes once the size is known', () => {
    const message = describeModel(
      readiness({ state: 'downloading', bytesDone: 1024 ** 3, bytesTotal: 4 * 1024 ** 3, fraction: 0.25 }),
    )

    expect(message).toBe('Getting the search model. 1.0 of 4.0 GB.')
  })

  it('separates reading the model off disk from fetching it', () => {
    expect(describeModel(readiness({ state: 'loading' }))).toBe('Starting the search model.')
  })
})
