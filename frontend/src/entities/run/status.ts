import type { Run } from '@/shared/api/types'
import { haltReason } from './lib'

/**
 * A run's state as one sentence a buyer understands, then one that explains it.
 *
 * Pyramid order: the answer ("your novel is ready"), then why, then — elsewhere,
 * folded — the technical record. The stage codes (`FLOW-3`) belong to the
 * record; a reader is told the step in words.
 */
export type Tone = 'ok' | 'live' | 'halt'

export interface PlainStatus {
  tone: Tone
  label: string
  headline: string
  step: string | null
  detail: string
}

const STEPS: Record<string, string> = {
  'FLOW-0': 'checking the order',
  'FLOW-1': 'building the world of the story',
  'FLOW-2': 'creating the characters',
  'FLOW-3': 'planning the chapters',
  'FLOW-4': 'writing and checking the chapters',
  'FLOW-5': 'giving the chapters one voice',
  'FLOW-6': 'putting the book together',
}

export function stepOf(stage: string): string {
  return STEPS[stage] ?? `step ${stage}`
}

/** `published` is whether a version of the book exists: `undefined` when not
 *  asked, `false` when asked and there is none. A run can end "complete" with
 *  no book — case 10 closed one under budget pressure without its last chapter. */
export function plainStatus(run: Run, live: boolean, published?: boolean): PlainStatus {
  // A live stream is proof of life; a halted row can be stale (red-team case 13).
  if (live || (!run.halted && run.stage !== 'complete')) {
    const step = stepOf(run.stage)
    return {
      tone: 'live',
      label: 'Being written',
      headline: 'Your novel is being written',
      step,
      detail: `Right now: ${step}. This page updates by itself.`,
    }
  }
  // A published book is the answer a buyer wants, whatever the row says after.
  if (run.halted && published !== true) {
    return {
      tone: 'halt',
      label: 'Stopped',
      headline: 'This novel stopped before the end',
      step: null,
      detail: `Why: ${haltReason(run)}. Everything it wrote is kept and readable.`,
    }
  }
  if (published === false) {
    return {
      tone: 'halt',
      label: 'No book',
      headline: 'This run ended without publishing a book',
      step: null,
      detail: 'Its last chapter never passed the checks, so there is nothing to read. The drafts are kept under Technical details.',
    }
  }
  return {
    tone: 'ok',
    label: 'Ready to read',
    headline: 'Your novel is ready',
    step: null,
    detail: 'Open Read to see the book. If a detail is wrong, Ask for a change.',
  }
}

const SMALL = new Set(['a', 'an', 'and', 'at', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'with'])

/** The book's title for display: the server's (`backend/commons/title.py`), or
 *  the slug's own words capitalised — never the slug with its hyphens. */
export function titleOf(run: Run): string {
  if (run.title) return run.title
  return run.slug
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((w, i) => (i > 0 && SMALL.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ')
}
