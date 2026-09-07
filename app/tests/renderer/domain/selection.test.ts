import { describe, expect, it } from 'vitest'
import { moveSelection, retainSelection } from '../../../src/renderer/domain/selection'

const rows = ['a', 'b', 'c']

describe('moveSelection', () => {
  it('selects the first row when nothing is selected and the user presses down', () => {
    expect(moveSelection(null, rows, 1)).toBe('a')
  })

  it('selects the last row when nothing is selected and the user presses up', () => {
    expect(moveSelection(null, rows, -1)).toBe('c')
  })

  it('stops at the end rather than wrapping', () => {
    expect(moveSelection('c', rows, 1)).toBe('c')
    expect(moveSelection('a', rows, -1)).toBe('a')
  })

  it('starts over when the selected row is no longer in the list', () => {
    expect(moveSelection('gone', rows, 1)).toBe('a')
  })

  it('has nothing to select in an empty list', () => {
    expect(moveSelection('a', [], 1)).toBeNull()
  })
})

describe('retainSelection', () => {
  it('keeps a selection that is still on screen', () => {
    expect(retainSelection('b', rows)).toBe('b')
  })

  it('drops a selection the new results do not contain', () => {
    expect(retainSelection('b', ['x', 'y'])).toBeNull()
  })
})
