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
  /** SPEC-006. The only one that judges how a chapter is written rather than
   *  whether it is correct — and the least reproducible of the six. */
  | 'prose'

export const CHARACTERISTICS: Characteristic[] = [
  'continuity',
  'science',
  'outline',
  'length',
  'chatter',
  'prose',
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
  /** null when no call reported a token figure. Never 0 to mean "not recorded". */
  input_tokens: number | null
  output_tokens: number | null
  /** How the token figures were obtained. Today: absent, on every real run. */
  tokens_provenance: Provenance
  /** The run's own measured total when there is one, else the sum of the calls,
   *  else null. Never 0 to mean "nothing recorded". */
  total_usd: number | null
  /** What the sum over `calls` comes to. A floor when a measured total exists. */
  summed_from_calls_usd: number | null
  /** How `total_usd` was obtained. The run total can be measured while the
   *  per-call split is absent, which is exactly today's situation. */
  total_provenance: Provenance
  /** The grade of each individual call. */
  provenance: Provenance[]
  turns: number | null
  duration_ms: number | null
  subagent_dispatches: number | null
}

/**
 * Four states, not two.
 *
 * `unchecked` is not `conformant`: a run with nothing to judge has not been
 * found obedient, it has not been looked at. `not_applicable` marks a run judged
 * by a rule that did not exist yet — applying today's to it measures nothing.
 */
export type ConformanceVerdict = 'conformant' | 'breached' | 'unchecked' | 'not_applicable'

export interface Conformance {
  attempts_checked: number
  /** Attempts with no aggregate. Unjudgeable, which is not the same as clean. */
  unjudgeable: number
  breaches: string[]
  verdict: ConformanceVerdict
  why?: string
}

export interface Warning {
  /** Null when the warning is about the run, not a chapter. **Zero is a
   *  chapter** — it is the outline audit's slot — so this is checked against
   *  null, never for truthiness. A `warning.chapter ? ... : ''` hid it. */
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
  /** Did the run obey its own gate? Computed from the archive, not trusted. */
  conformance: Conformance
  /** What an imported run did NOT carry. A gap reads as a gap, never a zero. */
  completeness: Gap[]
  /** The orchestrator's own turns against the 100,000 ceiling: measured,
   *  shown, and never halted on — the ceiling is about the agents' packets
   *  (docs/spec.md §8). `provenance: 'absent'` means nobody watched this run;
   *  `turnsOverCeiling: 0` would mean somebody did and it never crossed. */
  orchestrator_context: OrchestratorContext
}

export interface OrchestratorContext {
  turns: number | null
  largest_turn_tokens: number | null
  turns_over_ceiling: number | null
  ceiling: number
  provenance: Provenance
  note: string
}

/* ------------------------------------------------------------------------- *
 * storyMaker: the brief, the book, and a reader's change.
 *
 * Same warning as above — these describe what the backend says it sends, not
 * what arrived. Everything that indexes into them guards first.
 * ------------------------------------------------------------------------- */

export interface Memory {
  text: string
  /** Absent far more often than present, and absent is `null`. Never "today"
   *  and never the epoch: the temporal validator reads these, and an invented
   *  date is an invented contradiction (`backend/brief/models.Memory`). */
  date: string | null
}

export interface Recipient {
  /** An alias and not a name: the brief travels through a model, a database and
   *  a PDF, and the less of a real person is in it the better. */
  alias: string
  /** Empty means unknown. An unknown age is unknown, not a newborn. */
  age: number | null
  pronouns: string
  traits: string[]
  relationship_to_buyer: string
}

export interface Brief {
  occasion: string
  recipient: Recipient
  memories: Memory[]
  genre: string
  tone: string
  length_chapters: number
  forbidden_terms: string[]
  mandatory_facts: string[]
  dedication: string
  /** The one field the buyer writes freely, which makes it the one field an
   *  attacker controls. Carried as data, shown labelled, never placed inside an
   *  instruction (SPEC-EXAM-002 §5.3, AC-3). */
  free_text: string
}

/** `ok` is the only value that may enable *Write it*. */
export type CheckStatus = 'ok' | 'incomplete' | 'contradiction' | 'invalid'

export interface CheckResult {
  status: CheckStatus
  questions: string[]
  contradictions: string[]
  /** Only for `invalid`: the schema's own complaints. */
  errors: string[]
}

export interface FactRow {
  id: number
  kind: string
  text: string
  /** `brief` is a promise the publish gate checks for; `freetext` is a lead for
   *  a human. Same table, different trust. */
  source: string
  mandatory: boolean
  /** `[]` is a fact with no usage rows — not a fact used in chapter zero. */
  chapters: number[]
}

export interface Impact {
  fact_id: number
  text: string
  kind: string
  source: string
  mandatory: boolean
  version: number
  chapters: number[]
  /** Always false, and sent on every answer so no page can present this list as
   *  the complete one. */
  exact: boolean
  matching: string
}

export interface VersionRow {
  n: number
  /** The version this one was made from; null for the first. */
  parent: number | null
  reason: string
  created_at: string
  /** Read off the disk, not assumed from the row: the print needs a browser and
   *  can fail where the publish did not. */
  pdf: boolean
}

export interface ChapterEntry {
  n: number
  title: string
}

export interface CharacterEntry {
  canonical_name: string
  role: string | null
  birth_date: string | null
  /** null when no chapter was recorded for them. Absent, not chapter zero. */
  first_chapter: number | null
}

export interface PlaceEntry {
  canonical_name: string
  note: string | null
  first_chapter: number | null
}

/** What `POST /api/runs/{id}/changes` answers: a plan, not a finished book. */
export interface ChangePlan {
  run_id: string
  fact_id: number | string
  chapters: number[]
  version: number
  status: string
}
