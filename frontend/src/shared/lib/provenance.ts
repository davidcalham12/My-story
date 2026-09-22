import type { Cost, Provenance } from '@/shared/api/types'

/**
 * How a figure was obtained, and how to say so.
 *
 * The project's rule, in one function: **what cannot be measured is reported as
 * unmeasurable, never as zero.** A run that destroyed its evidence and a run
 * where nothing happened are identical in a number and must not be identical on
 * screen.
 */

export const MARK: Record<Provenance, string> = {
  measured: '●',
  reported: '◐',
  reconstructed: '◌',
  estimated: '≈',
  absent: '—',
}

export const MEANING: Record<Provenance, string> = {
  measured: 'counted by something that was there',
  reported: 'stated by whoever did the work',
  reconstructed: 'rebuilt afterwards from what survived',
  estimated: 'derived from a rule of thumb',
  absent: 'not recorded — which is not the same as zero',
}

/**
 * How the displayed total was obtained.
 *
 * The backend decides this, because it is the only side that knows whether the
 * run reported its own total. **A measured run total is measured even when the
 * per-call split is absent** — which is today's situation exactly: Claude Code's
 * `result` event gives the whole run's cost, and the per-agent packets report
 * nothing. Grading the total by its weakest call would file $18.82 of measured
 * money as unrecorded.
 */
export function gradeOf(cost: Cost | undefined): Provenance {
  return cost?.total_provenance ?? weakestCall(cost)
}

/** The weakest grade across the individual calls, for the per-call series. */
export function weakestCall(cost: Cost | undefined): Provenance {
  const order: Provenance[] = ['absent', 'estimated', 'reconstructed', 'reported', 'measured']
  const present = cost?.provenance ?? []
  for (const grade of order) if (present.includes(grade)) return grade
  return 'absent'
}

export function money(cost: Cost | undefined): string {
  if (!cost) return 'not recorded'
  // null is the backend saying "absent". It used to have to say 0, because the
  // column could not be null, and 0 and absent are not the same claim.
  if (cost.total_usd === null || cost.total_usd === undefined) return 'not recorded'
  if (!cost.total_usd && !cost.calls) return 'not recorded'
  return `$${cost.total_usd.toFixed(2)}`
}
