import { describe, expect, it } from 'vitest'
import type { Attempt, Cost, Run } from '@/shared/api/types'
import { acceptedAttempt, bestAttempt, chapters, haltReason, unscored, worst } from './lib'
import { gradeOf, money, tokens, weakestCall } from '@/shared/lib/provenance'

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

describe('provenance', () => {
  const cost = (over: Partial<Cost>): Cost => ({
    calls: 10, input_tokens: 1, output_tokens: 1, tokens_provenance: 'measured',
    total_usd: 1,
    summed_from_calls_usd: 1, total_provenance: 'measured',
    provenance: ['measured'], turns: null, duration_ms: null,
    subagent_dispatches: null, ...over,
  })

  it('grades the total by how the total was obtained', () => {
    expect(gradeOf(cost({ total_provenance: 'reconstructed' }))).toBe('reconstructed')
    expect(gradeOf(cost({ total_provenance: 'absent' }))).toBe('absent')
  })

  it('keeps a measured total measured when the per-call split is absent', () => {
    // Today's situation exactly: Claude Code's result event gives the whole
    // run's cost, and the per-agent packets report nothing. Grading the total
    // by its weakest call would file $18.82 of measured money as unrecorded.
    const c = cost({ total_provenance: 'measured', provenance: ['absent'] })
    expect(gradeOf(c)).toBe('measured')
    expect(weakestCall(c)).toBe('absent')
  })

  it('takes the weakest grade across the calls, because a series is only as good as its worst part', () => {
    expect(weakestCall(cost({ provenance: ['measured', 'reconstructed'] }))).toBe('reconstructed')
    expect(weakestCall(cost({ provenance: ['measured'] }))).toBe('measured')
  })

  it('says "not recorded" for a token count nobody reported', () => {
    // The panel printed "0 / 0" tokens for a run that spent $18.82. Every call
    // had stored NULL, honestly; a COALESCE in the query turned the truth into
    // a zero on the way out.
    expect(tokens(null)).toBe('not recorded')
    expect(tokens(undefined)).toBe('not recorded')
    expect(tokens(0)).toBe('0')
    expect(tokens(1234567)).toMatch(/1.234.567/)
  })

  it('says "not recorded" rather than zero', () => {
    // A run that destroyed its evidence and a run where nothing happened are
    // identical in a number and must not be identical on screen.
    expect(money(cost({ calls: 0, total_usd: 0 }))).toBe('not recorded')
    expect(money(cost({ total_usd: null }))).toBe('not recorded')
    expect(money(undefined)).toBe('not recorded')
    expect(money(cost({ total_usd: 49.33 }))).toBe('$49.33')
  })
})

describe('halts', () => {
  const run = (halted: string | null): Run => ({
    id: 'r', slug: 's', premise: 'p', profile: 'tiny', tone: null,
    stage: 'FLOW-4', halted, halted_detail: null, source: 'v2',
    started_at: '', finished_at: null,
  })

  it('explains each halt in words a reader can act on', () => {
    expect(haltReason(run('gate'))).toContain('not put in the book')
    expect(haltReason(run('budget'))).toContain('kept')
    expect(haltReason(run('context'))).toContain('token ceiling')
    expect(haltReason(run(null))).toBeNull()
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
