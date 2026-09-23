import { defineConfig } from 'vite'
import path from 'node:path'

export default defineConfig({
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  // `css: true` because the default stubs every stylesheet to an empty string,
  // including one imported with `?raw`. `identity.test.ts` reads the palette out
  // of `tokens.css`; with the stub it read "" and passed over nothing — the way
  // a rule stops being enforced without anyone noticing.
  test: { environment: 'node', css: true },
})
