import { describe, expect, it } from 'vitest'

/**
 * AC-8, and the reason it is a test rather than a review note.
 *
 * The identity is Qaracter's and it is not ours to invent. A hex code typed
 * into a component is a colour that was never decided — it survives a redesign,
 * it is invisible to a grep for `--brand`, and it is how the previous panel
 * ended up with four different oranges none of which was the brand's.
 *
 * So: one file holds the palette and the type, and nothing else names a colour
 * or a typeface. `tokens.css` is that file, and it is the only exemption.
 *
 * Read through Vite's own glob rather than `node:fs`, like `figures.test.ts`,
 * so the suite still needs no `@types/node`.
 */

const SOURCES = import.meta.glob('../../**/*.{tsx,ts,css}', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

// Glob keys are relative to this file, so the exemption is matched by name —
// the same string the filter below uses, so the two cannot disagree.
const TOKENS = 'tokens.css'

const GOVERNED = Object.entries(SOURCES).filter(
  ([path]) => !path.includes('.test.') && !path.endsWith('tokens.css'),
)

/** `#233441`, `#FF7932`, `#fff` — three, six or eight digits. */
const HEX = /#[0-9a-fA-F]{3,8}\b/

/** A family named rather than inherited or read from a token. */
const FONT = /font-family:(?!\s*var\()|font:(?!\s*(inherit|var\())/

describe('the identity lives in one file', () => {
  it('finds the sources at all, so a rename cannot make this pass by emptiness', () => {
    expect(GOVERNED.length).toBeGreaterThan(8)
    // Vitest stubs stylesheets to "" unless `css: true`, and the colour rule
    // is about stylesheets above all. Read as "" it passed over nothing.
    for (const [path, text] of GOVERNED) {
      if (path.endsWith('.css')) expect(text.length, `${path} read as empty`).toBeGreaterThan(0)
    }
  })

  it('has a tokens file for the palette to live in', () => {
    expect(Object.keys(SOURCES).some((p) => p.endsWith(TOKENS))).toBe(true)
  })

  it('declares the Qaracter palette there, by its brand values', () => {
    const tokens = Object.entries(SOURCES).find(([p]) => p.endsWith(TOKENS))?.[1] ?? ''
    for (const value of ['#FF7932', '#F4631E', '#233441', '#1E2D3D', '#F5F5F5']) {
      expect(tokens.toUpperCase(), `tokens.css is missing ${value}`).toContain(value)
    }
    expect(tokens).toContain('DM Sans')
  })

  it('contains no hex colour anywhere else', () => {
    for (const [path, text] of GOVERNED) {
      for (const [i, line] of text.split('\n').entries()) {
        expect(HEX.test(line), `${path}:${i + 1} names a colour — ${line.trim()}`).toBe(false)
      }
    }
  })

  it('names no typeface anywhere else', () => {
    for (const [path, text] of GOVERNED) {
      for (const [i, line] of text.split('\n').entries()) {
        expect(FONT.test(line), `${path}:${i + 1} names a typeface — ${line.trim()}`).toBe(false)
      }
    }
  })
})

/**
 * Feature-Sliced Design's one hard rule, held by a test.
 *
 * `pages/run` imported `pages/quality` — sideways, between two slices of the
 * same layer — and the cost was not theoretical: the gate table could not be
 * shown anywhere a page did not already exist, and deleting the Quality page
 * would have broken the Run page. Imports go downward only:
 * `app → pages → features → entities → shared`.
 */

const BELOW: Record<string, string[]> = {
  app: ['pages', 'features', 'entities', 'shared'],
  pages: ['features', 'entities', 'shared'],
  features: ['entities', 'shared'],
  entities: ['shared'],
  shared: [],
}

const layerOf = (path: string): string | null =>
  /\/(app|pages|features|entities|shared)\//.exec(path)?.[1] ?? null

describe('imports go downward only', () => {
  it('lets no slice import from its own layer or above it', () => {
    for (const [path, text] of GOVERNED) {
      const from = layerOf(path)
      if (!from) continue
      for (const match of text.matchAll(/from '@\/(\w+)\//g)) {
        const to = match[1] as string
        expect(
          BELOW[from]?.includes(to),
          `${path}: ${from}/ imports ${to}/ — FSD allows ${BELOW[from]?.join(', ')}`,
        ).toBe(true)
      }
    }
  })
})
