import type { Impact, VersionRow } from '@/shared/api/types'

/**
 * A published version of the novel, and what it changed.
 *
 * The `versions` table records why a version was published and not which
 * chapters it touched (migration 012), so the band at the top of *Read* has to
 * ask the fact the change was made to — the same `fact_usage` rows that decided
 * which chapters to rewrite. When the reason names no fact, the answer is that
 * it was not recorded, in words. An empty list would say "this version changed
 * nothing", and a regeneration that touches no chapter is refused before it
 * starts, so that is the one thing it certainly did not do.
 */

/** The string `backend/versions/change.py` publishes a reader change with. */
const READER_CHANGE = /reader change to fact (\S+)/i

export function factOfReason(reason: string): string | null {
  return READER_CHANGE.exec(reason ?? '')?.[1] ?? null
}

export interface Changed {
  chapters: number[]
  /** False means "nobody wrote it down", never "none". */
  recorded: boolean
}

export function changedIn(version: VersionRow, impact: Impact | null): Changed {
  if (version.n <= 1 || !factOfReason(version.reason)) return { chapters: [], recorded: false }
  if (!impact) return { chapters: [], recorded: false }
  return { chapters: [...impact.chapters].sort((a, b) => a - b), recorded: true }
}

/** The highest published version, or null while there is none. */
export function current(versions: VersionRow[]): number | null {
  if (!versions.length) return null
  return Math.max(...versions.map((v) => v.n))
}
