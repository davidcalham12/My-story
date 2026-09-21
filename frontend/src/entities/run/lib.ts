import type { Attempt, Characteristic, Run } from '@/shared/api/types'
import { CHARACTERISTICS } from '@/shared/api/types'

export const THRESHOLD = 8

/** Why a run stopped, in words a reader can act on. */
export function haltReason(run: Run): string | null {
  if (!run.halted) return null
  const reasons: Record<string, string> = {
    gate: 'a chapter failed three attempts and the patch, so it was not put in the book',
    budget: 'the cost ceiling was reached; the attempt in flight was kept',
    context: 'a context packet exceeded the token ceiling',
    interrupted: 'the process died; what it produced is still here',
  }
  return reasons[run.halted] ?? run.halted
}

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
