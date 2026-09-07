import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // Most tests are plain Node (domain, main). Files that render a hook or
    // component opt into jsdom individually via a `@vitest-environment` docblock.
    environment: 'node',
    include: ['tests/**/*.test.{ts,tsx}'],
  },
})
