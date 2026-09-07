import { BrowserWindow, session, shell } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

const CONTENT_SECURITY_POLICY = [
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

function applyContentSecurityPolicy(): void {
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [CONTENT_SECURITY_POLICY],
      },
    })
  })
}

export interface CreateMainWindowOptions {
  preloadPath: string
  sidecarToken: string
  initialBaseUrl?: string
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

  window.once('ready-to-show', () => window.show())

  const rendererUrl = process.env['ELECTRON_RENDERER_URL']
  if (rendererUrl) {
    void window.loadURL(rendererUrl)
  } else {
    void window.loadFile(path.join(__dirname, '../renderer/index.html'))
  }

  return window
}
