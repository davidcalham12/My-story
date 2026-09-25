import type { Provenance } from '@/shared/api/types'

/** SPEC-EXAM-008: one change to a novel and what it cost, as `/costs` returns it. */
export type ChangeKind = 'generate' | 'continue' | 'reader_change' | 'redo'

export interface Figures {
  total_usd: number | null
  orchestrator_usd: number | null
  agents_usd: number | null
}

export interface ChangeCost extends Figures {
  n: number
  kind: ChangeKind
  label: string | null
  version: number | null
  chapters: number[] | null
  started_at: string | null
  finished_at: string | null
  /** Σ result.duration_ms, measured by Claude Code. null: absent. */
  minutes: number | null
  orchestrator_model: string | null
  agents_model: string | null
  provenance: Provenance | null
  note: string | null
  results: number | null
  unresulted: number | null
  /** Processes that ended without a `result`: their cost is absent. */
  incomplete: number
  no_orchestrator: boolean
  source: 'langfuse' | 'local' | 'both'
  confirmed: boolean
  status: string
  trace_id: string
  trace_url: string | null
  disagreement: { local: Figures; langfuse: Figures } | null
}

export interface CostTotal {
  usd: number | null
  provenance: Provenance
  changes: number
  /** Changes with no figure: counted, never added as 0. */
  absent: number
  incomplete: number
  source: 'langfuse' | 'local' | 'mixed'
}

export interface RunCosts {
  run_id: string
  session_id: string
  langfuse: 'ok' | 'unreachable' | 'not configured' | 'not asked'
  rows: ChangeCost[]
  total: CostTotal
}
