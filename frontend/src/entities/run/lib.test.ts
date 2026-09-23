import { describe, expect, it } from 'vitest'
import type { Cost, Run } from '@/shared/api/types'
import { haltReason } from './lib'
import { gradeOf, money, tokens, weakestCall } from '@/shared/lib/provenance'

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
