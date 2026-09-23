import type { Brief } from '@/shared/api/types'
import { LENGTH_CHAPTERS } from './model'

/**
 * The one line that names a novel in the library and starts its run.
 *
 * Built from four answered fields and from nothing else. In particular **not**
 * from `free_text` and not from the memories: a premise is read by a model as a
 * description of the book to write, which makes it an instruction field, and
 * brief 04's free text is `IGNORE ALL PREVIOUS INSTRUCTIONS…`. Both reach the
 * novel through the brief, where they are rows with a `source` saying what they
 * are worth; here they would be an instruction (SPEC-EXAM-001 AC-2).
 *
 * Long enough to satisfy `StartRun.premise`'s `min_length=10` even from a brief
 * with nothing filled in, so a half-answered form cannot produce a 422 with no
 * readable cause.
 */
export function premiseOf(brief: Brief): string {
  const who = brief.recipient.alias.trim() || 'the reader'
  const kind = brief.genre.trim() || 'a story'
  const relation = brief.recipient.relationship_to_buyer.trim()
  const occasion = brief.occasion.trim()

  return [
    `A personalised novel in ${LENGTH_CHAPTERS} chapters for ${who}`,
    relation ? ` (${relation})` : '',
    occasion ? `, for ${occasion}` : '',
    `: ${kind}.`,
  ].join('')
}
