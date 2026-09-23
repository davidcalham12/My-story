import type { Attempt, Characteristic } from '@/shared/api/types'
import { CHARACTERISTICS } from '@/shared/api/types'

/**
 * What the critics said about a draft, read back.
 *
 * These live beside the table that shows them rather than in `entities/run`,
 * because both the Run page and the Quality page need them and an entity that
 * imports a sibling entity is the same sideways import that `pages/run ->
 * pages/quality` already was. An attempt's score is the critique's, not the
 * run's.
 */

export const THRESHOLD = 8

/** The attempt a chapter shipped on, or null when it never passed. */
export function acceptedAttempt(attempts: Attempt[], chapter: number): Attempt | null {
  return attempts.find((a) => a.chapter === chapter && a.promoted) ?? null
}

/**
 * The best attempt, which is not always the accepted one.
 *
 * A chapter whose first attempt scored 7 and whose third scored 4 ships the 7.
 */
export function bestAttempt(attempts: Attempt[], chapter: number): Attempt | null {
  const mine = attempts.filter((a) => a.chapter === chapter)
  if (!mine.length) return null
  return mine.reduce((best, a) =>
    (a.aggregate ?? -1) > (best.aggregate ?? -1) ? a : best,
  )
}

/** Characteristics that produced no usable verdict. Excluded, not failed. */
export function unscored(attempt: Attempt): Characteristic[] {
  return CHARACTERISTICS.filter((c) => attempt.scores[c] === null)
}

export function worst(attempt: Attempt): Characteristic[] {
  const scored = CHARACTERISTICS.filter((c) => typeof attempt.scores[c] === 'number')
  if (!scored.length) return []
  const low = Math.min(...scored.map((c) => attempt.scores[c] as number))
  return scored.filter((c) => attempt.scores[c] === low)
}

export const chapters = (attempts: Attempt[]): number[] =>
  [...new Set(attempts.map((a) => a.chapter))].sort((a, b) => a - b)
