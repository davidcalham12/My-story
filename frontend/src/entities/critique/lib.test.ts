import { describe, expect, it } from 'vitest'
import type { Attempt } from '@/shared/api/types'
import { acceptedAttempt, bestAttempt, chapters, unscored, worst } from './lib'

/**
 * Moved here with the code it tests, unchanged.
 *
 * An attempt's score is the critique's, not the run's; `entities/run` now holds
 * only what is true of a run. The assertions are the ones that were already
 * green in `entities/run/lib.test.ts`, so the move is a refactor and not a
 * rewrite.
 */

const attempt = (over: Partial<Attempt>): Attempt => ({
  chapter: 1,
  attempt: 1,
  aggregate: 10,
  verdict: 'accept',
  promoted: false,
  scores: { continuity: 10, science: 10, outline: 10, length: 10, chatter: 10 },
  ...over,
})

describe('which draft shipped', () => {
  it('keeps the best attempt, which is not always the last', () => {
    // A chapter scoring 7 then 5 then 4 must show the 7. A rewrite is not
    // guaranteed to improve, and the panel must not imply it was.
    const attempts = [
      attempt({ attempt: 1, aggregate: 7 }),
      attempt({ attempt: 2, aggregate: 5 }),
      attempt({ attempt: 3, aggregate: 4 }),
    ]
    expect(bestAttempt(attempts, 1)?.attempt).toBe(1)
  })

  it('distinguishes the accepted draft from the best one', () => {
    const attempts = [
      attempt({ attempt: 1, aggregate: 7 }),
      attempt({ attempt: 2, aggregate: 9, promoted: true }),
    ]
    expect(acceptedAttempt(attempts, 1)?.attempt).toBe(2)
    expect(bestAttempt(attempts, 1)?.attempt).toBe(2)
  })

  it('reports no shipped draft when the gate halted', () => {
    const attempts = [attempt({ aggregate: 4 }), attempt({ attempt: 2, aggregate: 4 })]
    expect(acceptedAttempt(attempts, 1)).toBeNull()
  })
})

describe('scores', () => {
  it('treats a null score as unscored, never as a failure', () => {
    // 10 would invent an approval and 0 a rejection. Neither is honest, and
    // returning 10 here once let a malformed reply pass a draft silently.
    const a = attempt({ scores: { continuity: 10, science: null, outline: 10, length: 10, chatter: 10 } })
    expect(unscored(a)).toEqual(['science'])
    expect(worst(a)).toEqual(['continuity', 'outline', 'length', 'chatter'])
  })

  it('names every characteristic that produced the minimum', () => {
    const a = attempt({ scores: { continuity: 4, science: 4, outline: 10, length: 10, chatter: 10 } })
    expect(worst(a)).toEqual(['continuity', 'science'])
  })
})

describe('chapters', () => {
  it('lists each chapter once, in order', () => {
    const attempts = [
      attempt({ chapter: 2 }), attempt({ chapter: 1 }), attempt({ chapter: 2, attempt: 2 }),
    ]
    expect(chapters(attempts)).toEqual([1, 2])
  })
})
