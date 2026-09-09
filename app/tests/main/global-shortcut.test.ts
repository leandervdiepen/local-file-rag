import { describe, expect, it } from 'vitest'
import { toggle, type ToggleTarget } from '../../src/main/global-shortcut'

/** A real window stand-in that records what was done to it. */
function aWindow(state: { visible: boolean; focused: boolean }) {
  const calls: string[] = []
  const window: ToggleTarget & { calls: string[] } = {
    calls,
    isVisible: () => state.visible,
    isFocused: () => state.focused,
    show: () => {
      state.visible = true
      calls.push('show')
    },
    focus: () => {
      state.focused = true
      calls.push('focus')
    },
    hide: () => {
      state.visible = false
      calls.push('hide')
    },
  }
  return window
}

describe('the open shortcut', () => {
  it('brings a hidden window up and focuses it', () => {
    const window = aWindow({ visible: false, focused: false })

    toggle(window)

    expect(window.calls).toEqual(['show', 'focus'])
  })

  it('brings a window that is behind something to the front rather than hiding it', () => {
    const window = aWindow({ visible: true, focused: false })

    toggle(window)

    expect(window.calls).toEqual(['show', 'focus'])
  })

  it('dismisses the window the user is already looking at', () => {
    const window = aWindow({ visible: true, focused: true })

    toggle(window)

    expect(window.calls).toEqual(['hide'])
  })

  it('opens again after being dismissed', () => {
    const state = { visible: true, focused: true }
    const window = aWindow(state)

    toggle(window)
    toggle(window)

    expect(window.calls).toEqual(['hide', 'show', 'focus'])
  })
})
