import { describe, expect, it } from 'vitest'
import type { Run } from '@/shared/api/types'
import { plainStatus } from './status'

const run = (over: Partial<Run>): Run => ({
  id: 'r', slug: 's', premise: 'p', profile: 'exam', tone: null, stage: 'FLOW-1',
  halted: null, halted_detail: null, source: 'v2', started_at: '', finished_at: null, ...over,
})

describe('plainStatus — the answer first, in words anyone reads', () => {
  it('says a finished novel is ready to read', () => {
    const s = plainStatus(run({ stage: 'complete', published_chapters: 3, chapters_planned: 3 }), false)
    expect(s.tone).toBe('ok')
    expect(s.headline).toMatch(/ready/i)
  })

  it('names the step a live novel is on, not its code', () => {
    const s = plainStatus(run({ stage: 'FLOW-3' }), true)
    expect(s.tone).toBe('live')
    expect(s.step).toMatch(/planning the chapters/i)
    expect(s.headline).not.toContain('FLOW')
  })

  it('believes the live stream over a stale halted row', () => {
    expect(plainStatus(run({ halted: 'process' }), true).tone).toBe('live')
  })

  it('says a stopped novel kept its work', () => {
    const s = plainStatus(run({ halted: 'budget', published_chapters: null }), false)
    expect(s.tone).toBe('halt')
    expect(s.detail).toMatch(/kept/i)
  })

  it('falls back to the raw stage it does not know rather than inventing one', () => {
    expect(plainStatus(run({ stage: 'FLOW-9' }), true).step).toContain('FLOW-9')
  })

  it('does not call a finished run ready when it published no book', () => {
    const s = plainStatus(run({ stage: 'complete', published_chapters: null, chapters_planned: 3 }), false)
    expect(s.tone).toBe('halt')
    expect(s.headline).not.toMatch(/ready/i)
    expect(s.label).toMatch(/no book/i)
  })

  // The owner saw "Ready to read" on 8834d0ab189a (budget) and 8ab6c57af9f6
  // (user), each with a one-chapter v1.
  it('(a) never calls a halted run ready, even when it published something', () => {
    for (const halted of ['budget', 'user']) {
      const s = plainStatus(run({ halted, published_chapters: 1, chapters_planned: 10 }), false)
      expect(s.tone).toBe('halt')
      expect(s.label).toBe('Stopped · partial book readable (1 of 10 chapters)')
      expect(s.headline).not.toMatch(/ready/i)
      expect(s.readable).toBe(true)
    }
  })

  it('(b) calls a finished run ready only when its latest version holds every planned chapter', () => {
    const eight = plainStatus(run({ stage: 'complete', published_chapters: 8, chapters_planned: 10 }), false)
    expect(eight.tone).not.toBe('ok')
    expect(eight.label).toBe('Stopped · partial book readable (8 of 10 chapters)')
    const ten = plainStatus(run({ stage: 'complete', published_chapters: 10, chapters_planned: 10 }), false)
    expect(ten.tone).toBe('ok')
    expect(ten.label).toBe('Ready to read')
  })

  it('(c) says "Checking…" while it does not know what was published, never a guess', () => {
    for (const over of [{ stage: 'complete' }, { halted: 'budget' }] as Partial<Run>[]) {
      const s = plainStatus(run(over), false)
      expect(s.label).toBe('Checking…')
      expect(s.tone).toBe('unknown')
      expect(s.readable).toBe(false)
    }
  })
})

describe('titleOf — the book, not the slug', () => {
  it('uses the title the server sends', async () => {
    const { titleOf } = await import('./status')
    expect(titleOf(run({ slug: 'x-y', title: 'The Key' } as Partial<Run>))).toBe('The Key')
  })
  it('turns a slug into words when there is no title', async () => {
    const { titleOf } = await import('./status')
    expect(titleOf(run({ slug: 'the-other-side-of-the-hill' }))).toBe('The Other Side of the Hill')
  })
})

describe('plainStatus — a complete run that published nothing', () => {
  it('is "No book", never "Ready to read" nor "Checking…" (leo-and-the-other-side-of-the-hill)', () => {
    const run = {
      id: '8dc162a1d8ec', slug: 'leo-and-the-other-side-of-the-hill', premise: 'p',
      profile: 'exam', tone: null, stage: 'complete', halted: null, halted_detail: null,
      published_chapters: null, chapters_planned: 10, published_versions: [],
    } as unknown as Run
    const status = plainStatus(run, false)
    expect(status.label).toBe('No book')
    expect(status.readable).toBe(false)
  })
})
