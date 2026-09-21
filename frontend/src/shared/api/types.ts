/**
 * The contract, as the backend states it.
 *
 * Not trusted at its type: `await res.json()` is `any` wearing an interface, and
 * a field the API stopped sending is `undefined` at runtime and typed present.
 * Everything that indexes into these guards first.
 */

export type Provenance =
  | 'measured'
  | 'reported'
  | 'reconstructed'
  | 'estimated'
  | 'absent'

export type Characteristic =
  | 'continuity'
  | 'science'
  | 'outline'
  | 'length'
  | 'chatter'

export const CHARACTERISTICS: Characteristic[] = [
  'continuity',
  'science',
  'outline',
  'length',
  'chatter',
]

export interface Run {
  id: string
  slug: string
  premise: string
  profile: string
  tone: string | null
  stage: string
  /** null while running; otherwise gate | budget | context | interrupted. */
  halted: string | null
  halted_detail: string | null
  /** `pre-loop003` runs were judged by a different set of characteristics and
   *  are excluded from statistics. Evidence, not sample. */
  source: 'v2' | 'pre-loop003'
  started_at: string
  finished_at: string | null
}

export interface Attempt {
  chapter: number
  attempt: number
  aggregate: number | null
  verdict: string | null
  promoted: boolean
  /** A score of `null` means the critic returned no usable verdict. It was
   *  EXCLUDED from the minimum — never counted as a 10, never as a 0. */
  scores: Partial<Record<Characteristic, number | null>>
}

export interface Cost {
  calls: number
  input_tokens: number
  output_tokens: number
  total_usd: number
  provenance: Provenance[]
}

export interface Warning {
  kind: string
  detail: string
  chapter: number | null
  ts: string
}

export interface Gap {
  field: string
  state: string
  note: string | null
}

export interface RunDetail {
  run: Run
  attempts: Attempt[]
  cost: Cost
  warnings: Warning[]
  /** What an imported run did NOT carry. A gap reads as a gap, never a zero. */
  completeness: Gap[]
}
