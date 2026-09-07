import { fileURLToPath } from 'node:url'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const rootDir = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: `${rootDir}src/main/main.ts`,
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: `${rootDir}src/preload/bridge.ts`,
      },
    },
  },
  renderer: {
    root: `${rootDir}src/renderer`,
    plugins: [react(), tailwindcss()],
    build: {
      rollupOptions: {
        input: `${rootDir}src/renderer/index.html`,
      },
    },
  },
})
