import { describe, expect, it } from 'vitest'
import type { Cost } from '@/shared/api/types'
import { projection } from './cost'

const cost = (total: number | null, over: Partial<Cost> = {}): Cost => ({
  calls: 4, input_tokens: null, output_tokens: null, tokens_provenance: 'absent',
  total_usd: total, summed_from_calls_usd: total, total_provenance: 'measured',
  provenance: ['measured'], turns: null, duration_ms: null,
  subagent_dispatches: null, ...over,
})

/**
 * What a novel is expected to cost, and why it is never a single number.
 *
 * Three figures because two novels of the same length have cost twice as much
 * as each other, and `estimated` because the sample is the handful of runs this
 * machine has done. The one thing this must not do is answer for a sample of
 * none: "$0.00" is a promise the system cannot keep, and it is the exact shape
 * of the bug that printed "0 / 0 tokens" for a run that spent $18.82.
 */

describe('what a novel is expected to cost', () => {
  it('answers nothing when nothing has been measured', () => {
    expect(projection([])).toBeNull()
    expect(projection([cost(null)])).toBeNull()
  })

  it('gives the lowest, the middle and the highest of what was measured', () => {
    const p = projection([cost(2), cost(9), cost(5)])
    expect(p?.low.total_usd).toBe(2)
    expect(p?.typical.total_usd).toBe(5)
    expect(p?.high.total_usd).toBe(9)
  })

  it('grades all three estimated, however well measured the runs were', () => {
    // Each past run's own total is measured. What the *next* novel will cost is
    // not: it is those figures used as a rule of thumb, which is what
    // `estimated` means and what the buyer is owed on that card.
    const p = projection([cost(2), cost(4)])
    for (const figure of [p?.low, p?.typical, p?.high]) {
      expect(figure?.total_provenance).toBe('estimated')
    }
  })

  it('ignores a run that reported no total rather than reading it as free', () => {
    const p = projection([cost(6), cost(null), cost(2)])
    expect(p?.low.total_usd).toBe(2)
    expect(p?.high.total_usd).toBe(6)
    expect(p?.runs).toBe(2)
  })
})
