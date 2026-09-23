import { describe, expect, it } from 'vitest'
import type { VersionRow } from '@/shared/api/types'
import { changedIn, current, factOfReason } from './lib'

const version = (over: Partial<VersionRow>): VersionRow => ({
  n: 1, parent: null, reason: 'first publication', created_at: '2026-09-23T10:00:00', pdf: true,
  ...over,
})

/**
 * Which chapters a version changed, and what to say when nobody wrote it down.
 *
 * `versions` records `reason` and not a chapter list (migration 012), so the
 * banner on *Read* has to get the chapters from the fact the change was made
 * to — the same `fact_usage` rows that decided which chapters to rewrite in the
 * first place. When the reason names no fact, the honest answer is that it was
 * not recorded. An empty list would say "this version changed nothing", which
 * is the one thing it certainly did not do.
 */

describe('what a version changed', () => {
  it('reads the fact out of a reader change', () => {
    // The string `backend/versions/change.py` writes when it publishes.
    expect(factOfReason('reader change to fact 7')).toBe('7')
    expect(factOfReason('reader change to fact a1b2')).toBe('a1b2')
  })

  it('reads no fact out of a first publication', () => {
    expect(factOfReason('first publication')).toBeNull()
    expect(factOfReason('')).toBeNull()
  })

  it('names the chapters the fact reached', () => {
    const changed = changedIn(version({ n: 2, parent: 1, reason: 'reader change to fact 7' }), {
      fact_id: 7, text: 'the dog is called Nala', kind: 'mandatory', source: 'brief',
      mandatory: true, version: 1, chapters: [3, 5, 7], exact: false, matching: 'words',
    })
    expect(changed.chapters).toEqual([3, 5, 7])
    expect(changed.recorded).toBe(true)
  })

  it('says the chapters were not recorded rather than showing none', () => {
    // A version that changed nothing does not exist: a regeneration that
    // touched no chapter is refused before it starts. "None" here would be a
    // lie in the reader's favour, which is the worst kind.
    const changed = changedIn(version({ n: 2, parent: 1, reason: 'reader change to fact 7' }), null)
    expect(changed.chapters).toEqual([])
    expect(changed.recorded).toBe(false)
  })

  it('has nothing to say about the first version', () => {
    expect(changedIn(version({ n: 1 }), null).recorded).toBe(false)
    expect(changedIn(version({ n: 1 }), null).chapters).toEqual([])
  })
})

describe('which version is the current one', () => {
  it('is the highest published, not the last row returned', () => {
    expect(current([version({ n: 2 }), version({ n: 1 }), version({ n: 3 })])).toBe(3)
  })

  it('is null when nothing has been published yet', () => {
    // The book is still being written. Zero is a version number; "none" is not.
    expect(current([])).toBeNull()
  })
})
