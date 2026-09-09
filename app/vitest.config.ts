import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // Most tests are plain Node (domain, main). Files that render a hook or
    // component opt into jsdom individually via a `@vitest-environment` docblock.
    environment: 'node',
    include: ['tests/**/*.test.{ts,tsx}'],
    // Bounded, because a test that spawns a process can otherwise wait for one
    // that never reports exiting, and a suite that hangs tells you less than
    // one that fails.
    testTimeout: 15_000,
    hookTimeout: 15_000,
  },
})
