import type { Run } from '@/shared/api/types'

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
