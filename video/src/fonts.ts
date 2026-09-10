import { loadFont } from '@remotion/fonts'
import { staticFile } from 'remotion'

// The same two variable faces the app bundles, embedded here rather than
// fetched: the README's network list is the product, and a font CDN is not on it.
export const fontsReady = Promise.all([
  loadFont({ family: 'Inter Variable', url: staticFile('fonts/inter-variable-latin.woff2'), weight: '100 900' }),
  loadFont({
    family: 'JetBrains Mono Variable',
    url: staticFile('fonts/jetbrains-mono-variable-latin.woff2'),
    weight: '100 800',
  }),
])
