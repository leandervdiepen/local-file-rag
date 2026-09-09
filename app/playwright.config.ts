import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  // Launching Electron starts a Python sidecar, which loads a four gigabyte
  // model before it can embed a page. This is minutes on a cold cache.
  timeout: 300_000,
  // One Electron at a time: they share the index directory and the GPU.
  workers: 1,
  fullyParallel: false,
  reporter: 'list',
})
