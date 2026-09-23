import type { RunDetail } from '@/shared/api/types'
import { GateTable } from '@/entities/critique/GateTable'

/**
 * The editor's screen: what was checked, and what each check said.
 *
 * It holds nothing of its own yet — the gate table moved down to
 * `entities/critique` because `pages/run` was importing this page to get it,
 * which FSD forbids and which made the Run page depend on a screen it has
 * nothing to do with. SPEC-EXAM-002 §4.6 grows here (the judge's six criteria,
 * the validators, the evals table) and the Run page will not notice.
 */
export function Quality({ detail }: { detail: RunDetail }) {
  return <GateTable detail={detail} />
}
