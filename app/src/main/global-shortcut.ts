import { globalShortcut, type BrowserWindow } from 'electron'

/**
 * Command Shift Space, because Command Space is Spotlight and this app is the
 * same motion for the files Spotlight is bad at.
 */
export const OPEN_SHORTCUT = 'CommandOrControl+Shift+Space'

export interface ToggleTarget {
  isVisible: () => boolean
  isFocused: () => boolean
  show: () => void
  focus: () => void
  hide: () => void
}

/**
 * Show the window, or hide it if it is already the window in front.
 *
 * Pressing the shortcut while looking at the app means dismiss. Pressing it
 * while the app is behind something means bring it here, which is not the same
 * as toggling on visibility alone: a window buried behind a browser is visible
 * and is not what the user is looking at.
 */
export function toggle(window: ToggleTarget): void {
  if (window.isVisible() && window.isFocused()) {
    window.hide()
    return
  }
  window.show()
  window.focus()
}

/**
 * Bind the shortcut, and report whether the OS gave it to us.
 *
 * A shortcut another app already owns is refused, and that is not a reason to
 * fail startup: the window still opens from the Dock and every other key still
 * works. The caller says so in the log rather than to the user, because there
 * is nothing for them to do about it until there is a settings screen.
 */
export function registerOpenShortcut(getWindow: () => BrowserWindow | null): boolean {
  return globalShortcut.register(OPEN_SHORTCUT, () => {
    const window = getWindow()
    if (window) toggle(window)
  })
}

export function unregisterOpenShortcut(): void {
  globalShortcut.unregister(OPEN_SHORTCUT)
}
