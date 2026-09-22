import { describe, expect, it } from 'vitest'

/**
 * G12, the "every" in "every figure carries its provenance".
 *
 * `Provenance.test.tsx` proves the mark renders. It cannot prove that the pages
 * actually put one next to each figure — and a grade the interface stores and
 * forgets to show is a grade nobody acts on.
 *
 * So this reads the pages as text. It is Analysis, not a render: it holds while
 * the source is that shape, which is the honest letter for it. It would not
 * catch a figure printed by some other helper, and that limit is the reason
 * `money()` is the only way a cost is allowed to reach the screen.
 *
 * Read through Vite's own glob rather than `node:fs`, so the suite needs no
 * `@types/node` and runs in the same environment as everything else here.
 */

const PAGES = import.meta.glob('../../pages/**/*.tsx', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

const SOURCES = Object.entries(PAGES).filter(([path]) => !path.includes('.test.'))

describe('no figure reaches the screen without its grade', () => {
  it('finds the pages at all, so a rename cannot make this pass by emptiness', () => {
    // A test that scans for files and asserts over nothing passes for the wrong
    // reason forever.
    expect(SOURCES.length).toBeGreaterThan(2)
  })

  it('accompanies every rendered money figure with a Provenance', () => {
    for (const [path, text] of SOURCES) {
      for (const line of text.split('\n')) {
        if (!line.includes('{money(')) continue
        expect(line, `${path}: a cost without its grade — ${line.trim()}`)
          .toContain('<Provenance')
      }
    }
  })

  it('imports Provenance wherever money is rendered', () => {
    for (const [path, text] of SOURCES) {
      if (!text.includes('{money(')) continue
      expect(text, `${path} renders money without importing Provenance`)
        .toContain("from '@/shared/ui/Provenance'")
    }
  })
})
