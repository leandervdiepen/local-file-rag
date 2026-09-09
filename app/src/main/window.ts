import { BrowserWindow, session, shell } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

const SHIPPED_POLICY = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  // The sidecar binds to loopback on a port the OS assigns (--port 0), so the
  // exact port is unknown until the handshake completes. The port wildcard
  // keeps the policy scoped to loopback only, never to a remote origin.
  "connect-src 'self' http://127.0.0.1:*",
].join('; ')

/**
 * The shipped policy plus what the Vite dev server needs, and nothing else.
 *
 * React Fast Refresh installs itself through an inline script. Under the
 * shipped policy that script is blocked, every component module then throws
 * "can't detect preamble" on import, and the window renders pure white with
 * the error only in a DevTools console nobody has open.
 *
 * `devOrigin` is the dev server this build was told to load, so the relaxation
 * cannot follow the app anywhere: it is off entirely in a packaged build,
 * where `ELECTRON_RENDERER_URL` is unset.
 */
function developmentPolicy(devOrigin: string): string {
  return SHIPPED_POLICY.replace("script-src 'self'", `script-src 'self' 'unsafe-inline' ${devOrigin}`).replace(
    "connect-src 'self' http://127.0.0.1:*",
    `connect-src 'self' http://127.0.0.1:* ${devOrigin} ${devOrigin.replace('http', 'ws')}`,
  )
}

export function contentSecurityPolicy(rendererUrl: string | undefined): string {
  if (!rendererUrl) return SHIPPED_POLICY
  return developmentPolicy(new URL(rendererUrl).origin)
}

function applyContentSecurityPolicy(): void {
  const policy = contentSecurityPolicy(process.env['ELECTRON_RENDERER_URL'])
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [policy],
      },
    })
  })
}

export interface CreateMainWindowOptions {
  preloadPath: string
  sidecarToken: string
  initialBaseUrl?: string
}

/**
 * Send what the renderer says to the terminal the app was started from.
 *
 * Without this a render-time exception is a white window and nothing else:
 * the message is in a DevTools console nobody has open, and the main process
 * log looks perfectly healthy. One blank screen cost an hour before this
 * existed.
 */
function reportRendererFailures(window: BrowserWindow): void {
  window.webContents.on('console-message', (event) => {
    if (event.level === 'error' || event.level === 'warning') {
      console.log(`[renderer] ${event.level}: ${event.message} (${event.sourceId}:${event.lineNumber})`)
    }
  })
  window.webContents.on('did-fail-load', (_event, code, description, url) => {
    console.log(`[renderer] failed to load ${url}: ${description} (${code})`)
  })
  window.webContents.on('render-process-gone', (_event, details) => {
    console.log(`[renderer] gone: ${details.reason}`)
  })
}

export function createMainWindow(options: CreateMainWindowOptions): BrowserWindow {
  applyContentSecurityPolicy()

  const window = new BrowserWindow({
    width: 960,
    height: 640,
    minWidth: 640,
    minHeight: 480,
    show: false,
    webPreferences: {
      preload: options.preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      additionalArguments: [
        `--sidecar-token=${options.sidecarToken}`,
        `--sidecar-base-url=${options.initialBaseUrl ?? ''}`,
      ],
    },
  })

  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https:')) {
      void shell.openExternal(url)
    }
    return { action: 'deny' }
  })

  reportRendererFailures(window)
  window.once('ready-to-show', () => window.show())

  const rendererUrl = process.env['ELECTRON_RENDERER_URL']
  if (rendererUrl) {
    void window.loadURL(rendererUrl)
  } else {
    void window.loadFile(path.join(__dirname, '../renderer/index.html'))
  }

  return window
}
