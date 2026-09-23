import type { Brief, Memory } from '@/shared/api/types'

/**
 * The brief as the form holds it, and what the check says about it.
 *
 * `backend/brief/models.py`: *eleven keys, and no twelfth. Adding one moves
 * SPEC-EXAM-001 §1 row 1, the interviewer's prompt and the frontend form
 * together.* `model.test.ts` holds the third of those three, by deriving the
 * form's field list from the shape of an empty brief rather than from a second
 * hand-written list that could drift from it.
 *
 * The form keeps `''` where the model keeps `null`. An input's value cannot be
 * null, and a state that loses the key entirely would post a brief with the
 * field missing — which the check would then never ask a question about.
 */

/** Fixed: the exam's novel is ten chapters, and `config/profiles/exam.json` is
 *  the only profile that writes that many. Shown, never editable. */
export const LENGTH_CHAPTERS = 10

export function emptyBrief(): Brief {
  return {
    occasion: '',
    recipient: { alias: '', age: null, pronouns: '', traits: [], relationship_to_buyer: '' },
    memories: [],
    genre: '',
    tone: '',
    length_chapters: LENGTH_CHAPTERS,
    forbidden_terms: [],
    mandatory_facts: [],
    dedication: '',
    free_text: '',
  }
}

/**
 * Every field of a brief, `recipient` flattened, in the order the form asks.
 *
 * Derived from an empty brief, so a key added to the model and not to the form
 * fails `model.test.ts` instead of quietly producing a novel written without
 * something the buyer was never asked for.
 */
export function keysOf(brief: Brief): string[] {
  return Object.keys(brief).flatMap((key) =>
    key === 'recipient'
      ? Object.keys(brief.recipient).map((sub) => `recipient.${sub}`)
      : [key],
  )
}

export const BRIEF_FIELDS: string[] = keysOf(emptyBrief())

/**
 * An eval brief, or a half-answered one, as form state.
 *
 * Two jobs, both of them failures avoided rather than features:
 *
 * - The fixture envelope (`id`, `purpose`) is dropped. Those keys are *about* a
 *   brief rather than part of one, and `Brief` forbids extras: loading an
 *   example into the form and posting it back would be a 422 nobody could read.
 * - Missing keys are filled from `emptyBrief()`. Brief 03 arrives with
 *   `tone: null` and `memories: []`, and a state that lost the key would post a
 *   brief without it — so the check would never ask its question.
 */
export function fromExample(raw: Record<string, unknown>): Brief {
  const base = emptyBrief()
  const recipient = (raw.recipient ?? {}) as Partial<Brief['recipient']>
  const memories = Array.isArray(raw.memories) ? (raw.memories as Partial<Memory>[]) : []
  const list = (value: unknown): string[] =>
    Array.isArray(value) ? value.map((v) => String(v)) : []
  const text = (value: unknown): string =>
    value === null || value === undefined ? '' : String(value)

  return {
    occasion: text(raw.occasion),
    recipient: {
      alias: text(recipient.alias),
      age: typeof recipient.age === 'number' ? recipient.age : null,
      pronouns: text(recipient.pronouns),
      traits: list(recipient.traits),
      relationship_to_buyer: text(recipient.relationship_to_buyer),
    },
    memories: memories.map((m) => ({ text: text(m.text), date: m.date ?? null })),
    genre: text(raw.genre),
    tone: text(raw.tone),
    length_chapters:
      typeof raw.length_chapters === 'number' ? raw.length_chapters : base.length_chapters,
    forbidden_terms: list(raw.forbidden_terms),
    mandatory_facts: list(raw.mandatory_facts),
    dedication: text(raw.dedication),
    free_text: text(raw.free_text),
  }
}

/**
 * What a brief has to say before `POST /api/briefs` is worth calling.
 *
 * This is what the form sends to `/check` and `/briefs`: `''` goes back to
 * `null` so an unanswered field reads as unanswered rather than as an answer of
 * no characters, which `_present` would count as filled for a string.
 */
export function forApi(brief: Brief): Record<string, unknown> {
  const orNull = (value: string) => (value.trim() === '' ? null : value)
  // The list editors keep an empty row at the end as their "add" control, and a
  // cleared row stays where it is until it is removed. Neither is an answer,
  // and a trait of "" would reach the Story Bible as a trait.
  const answered = (values: string[]) => values.filter((v) => v.trim() !== '')
  return {
    occasion: orNull(brief.occasion),
    recipient: {
      alias: orNull(brief.recipient.alias),
      age: brief.recipient.age,
      pronouns: orNull(brief.recipient.pronouns),
      traits: answered(brief.recipient.traits),
      relationship_to_buyer: orNull(brief.recipient.relationship_to_buyer),
    },
    memories: brief.memories
      .filter((m) => m.text.trim() !== '')
      .map((m) => ({ text: m.text, date: m.date })),
    genre: orNull(brief.genre),
    tone: orNull(brief.tone),
    length_chapters: brief.length_chapters,
    forbidden_terms: answered(brief.forbidden_terms),
    mandatory_facts: answered(brief.mandatory_facts),
    dedication: orNull(brief.dedication),
    free_text: brief.free_text,
  }
}

/**
 * Which field a question is about.
 *
 * Matched on the phrase that distinguishes each of `domain.REQUIRED`'s eight
 * questions rather than on the whole sentence, so a reworded question still
 * lands beside its field. When nothing matches the answer is `null` and the
 * page prints the question at the top of the form: wrong place beats
 * disappeared, and a reworded question that silently attached to `occasion`
 * would send the buyer to the wrong box.
 */
const ASKS: [string, RegExp][] = [
  ['recipient.alias', /what should the novel call/i],
  ['recipient.age', /how old is/i],
  ['recipient.relationship_to_buyer', /what is this person to you/i],
  ['occasion', /occasion/i],
  ['genre', /kind of story/i],
  ['tone', /what tone/i],
  ['memories', /memory|memories/i],
  ['length_chapters', /how many chapters/i],
]

export function fieldOfQuestion(question: string): string | null {
  return ASKS.find(([, pattern]) => pattern.test(question))?.[0] ?? null
}

/**
 * The fields a contradiction names, both of them.
 *
 * `domain._contradictions` writes the pair into the sentence on purpose —
 * "this brief is contradictory" is useless to the person who has to fix it —
 * so the page can show the warning beside each of the two answers that fought.
 */
export function fieldsOfContradiction(said: string): string[] {
  return BRIEF_FIELDS.filter((field) => said.includes(field))
}
