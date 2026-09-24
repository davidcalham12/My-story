import { describe, expect, it } from 'vitest'
import type { Run } from '@/shared/api/types'
import { plainStatus } from './status'

const run = (over: Partial<Run>): Run => ({
  id: 'r', slug: 's', premise: 'p', profile: 'exam', tone: null, stage: 'FLOW-1',
  halted: null, halted_detail: null, source: 'v2', started_at: '', finished_at: null, ...over,
})

describe('plainStatus — the answer first, in words anyone reads', () => {
  it('says a finished novel is ready to read', () => {
    const s = plainStatus(run({ stage: 'complete' }), false)
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
    const s = plainStatus(run({ halted: 'budget' }), false)
    expect(s.tone).toBe('halt')
    expect(s.detail).toMatch(/kept/i)
  })

  it('falls back to the raw stage it does not know rather than inventing one', () => {
    expect(plainStatus(run({ stage: 'FLOW-9' }), true).step).toContain('FLOW-9')
  })

  it('does not call a finished run ready when it published no book', () => {
    const s = plainStatus(run({ stage: 'complete' }), false, false)
    expect(s.tone).toBe('halt')
    expect(s.headline).not.toMatch(/ready/i)
    expect(s.label).toMatch(/no book/i)
  })

  it('calls a stopped run ready when it did publish a book', () => {
    expect(plainStatus(run({ halted: 'user' }), false, true).tone).toBe('ok')
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
