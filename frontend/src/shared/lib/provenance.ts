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

/** The weakest grade present, because a total is only as good as its worst part. */
export function gradeOf(cost: Cost | undefined): Provenance {
  const order: Provenance[] = ['absent', 'estimated', 'reconstructed', 'reported', 'measured']
  const present = cost?.provenance ?? []
  for (const grade of order) if (present.includes(grade)) return grade
  return 'absent'
}

export function money(cost: Cost | undefined): string {
  if (!cost || !cost.calls) return 'not recorded'
  if (!cost.total_usd) return 'not recorded'
  return `$${cost.total_usd.toFixed(2)}`
}
