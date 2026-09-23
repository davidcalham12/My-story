import type { Cost } from '@/shared/api/types'

/**
 * What the next novel is expected to cost, from what past ones did cost.
 *
 * Three figures and not one, because two novels of the same length have cost
 * twice as much as each other; and `estimated` on all three, because each past
 * run's own total being measured says nothing about the next one. That is the
 * difference between reporting a measurement and using it as a rule of thumb,
 * and the buyer is owed the second word on this card.
 *
 * A run that reported no total is dropped rather than counted as free. The
 * alternative is the bug that printed "0 / 0 tokens" for a run that spent
 * $18.82: a missing figure read as a zero.
 */

export interface Projection {
  low: Cost
  typical: Cost
  high: Cost
  /** How many measured novels are behind the three figures. Two is not a
   *  sample, and the screen says so rather than implying otherwise. */
  runs: number
}

export function projection(measured: Cost[]): Projection | null {
  const totals = measured
    .map((c) => c.total_usd)
    .filter((t): t is number => typeof t === 'number')
    .sort((a, b) => a - b)
  if (!totals.length) return null

  const at = (i: number): Cost => ({
    calls: 0,
    input_tokens: null,
    output_tokens: null,
    tokens_provenance: 'absent',
    total_usd: totals[i] as number,
    summed_from_calls_usd: null,
    total_provenance: 'estimated',
    provenance: ['estimated'],
    turns: null,
    duration_ms: null,
    subagent_dispatches: null,
  })

  return {
    low: at(0),
    typical: at(Math.floor((totals.length - 1) / 2)),
    high: at(totals.length - 1),
    runs: totals.length,
  }
}
