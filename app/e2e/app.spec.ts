import { _electron as electron, expect, test, type ElectronApplication, type Page } from '@playwright/test'
import { cpSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { homedir } from 'node:os'
import path from 'node:path'

/**
 * The money path, against the real app: index a folder, search it, open the
 * page and see why it matched.
 *
 * Everything here is the shipped code. The one thing the test does that a
 * person would not is add the folder through the sidecar rather than the
 * native picker, because a Playwright script cannot click an NSOpenPanel.
 */

const CORPUS = path.join(homedir(), 'demo-corpus')
const QUERY = 'egress'

let app: ElectronApplication
let page: Page
let folder: string
let userData: string

test.beforeAll(async () => {
  folder = mkdtempSync(path.join(tmpdir(), 'e2e-corpus-'))
  userData = mkdtempSync(path.join(tmpdir(), 'e2e-userdata-'))
  mkdirSync(folder, { recursive: true })
  cpSync(path.join(CORPUS, 'reports', 'invoices', 'hosting-q2-2026.pdf'), path.join(folder, 'hosting-q2-2026.pdf'))

  // Some shells export this, and it makes Electron run as plain node, where
  // `require('electron')` returns a path string and `app` is undefined.
  const env = { ...process.env }
  delete env['ELECTRON_RUN_AS_NODE']
  // `--user-data-dir` moves what Electron owns and the sidecar keeps its own
  // database, so without this the test indexed its temporary folder into the
  // developer's real index and left the folder registered there.
  env['LOCAL_FILE_RAG_DB'] = path.join(userData, 'db')

  app = await electron.launch({ args: ['.', `--user-data-dir=${userData}`], env })
  page = await app.firstWindow()
})

test.afterAll(async () => {
  await app?.close()
  rmSync(folder, { recursive: true, force: true })
  rmSync(userData, { recursive: true, force: true })
})

test('indexes a folder, finds a page in it, and shows why it matched', async () => {
  // Nothing here asserts a sentence. Copy is the most churned thing in the
  // app and a test that pins it fails on every rewrite while catching nothing.
  const baseUrl = await sidecarBaseUrl()
  await callSidecar(baseUrl, 'POST', '/folders', { path: folder })
  await callSidecar(baseUrl, 'POST', '/index/rescan')
  await page.reload()

  const box = page.getByRole('combobox')
  await expect(box).toBeVisible({ timeout: 60_000 })
  await expect.poll(async () => (await callSidecar(baseUrl, 'GET', '/index/stats')).pages_embedded, {
    timeout: 240_000,
    intervals: [2_000],
  }).toBeGreaterThan(0)

  await box.fill(QUERY)

  const result = page.getByText('hosting-q2-2026.pdf').first()
  await expect(result).toBeVisible({ timeout: 60_000 })

  // A thumbnail arrives as a blob URL, which the shipped content security
  // policy has to allow. It did not, and every result showed a broken image.
  const thumbnail = page.locator('img').first()
  await expect(thumbnail).toBeVisible({ timeout: 60_000 })
  expect(await thumbnail.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0)

  await box.press('ArrowDown')
  await box.press(' ')

  await expect(page.locator('canvas')).toBeVisible({ timeout: 120_000 })
})

async function sidecarBaseUrl(): Promise<string> {
  return page.evaluate(async () => {
    type State = { status: string; baseUrl?: string }
    const bridge = (window as unknown as { bridge: { onSidecarState: (f: (s: State) => void) => () => void } }).bridge
    return new Promise<string>((resolve, reject) => {
      const giveUp = setTimeout(() => reject(new Error('the sidecar never reported a base URL')), 120_000)
      const stop = bridge.onSidecarState((state) => {
        if (state.status === 'ready' && state.baseUrl) {
          clearTimeout(giveUp)
          stop()
          resolve(state.baseUrl)
        }
      })
    })
  })
}

async function callSidecar(baseUrl: string, method: string, route: string, body?: unknown): Promise<any> {
  return page.evaluate(
    async ([base, verb, path_, payload]) => {
      const token = (window as unknown as { bridge: { sidecar: { token: string } } }).bridge.sidecar.token
      const response = await fetch(base + path_, {
        method: verb,
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: payload === undefined ? undefined : JSON.stringify(payload),
      })
      const text = await response.text()
      return text ? JSON.parse(text) : {}
    },
    [baseUrl, method, route, body] as const,
  )
}
