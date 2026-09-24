import type { ReactNode } from 'react'
import type { Brief, CheckResult, Memory, Recipient } from '@/shared/api/types'
import {
  LENGTH_CHAPTERS,
  fieldOfQuestion,
  fieldsOfContradiction,
} from '@/entities/brief/model'
import type { Projection } from '@/entities/brief/cost'
import { gradeOf, money } from '@/shared/lib/provenance'
import { Provenance } from '@/shared/ui/Provenance'

/**
 * The interview, with nothing in it that fetches.
 *
 * Every answer arrives as a prop — the brief, the check, the projection — so
 * the test renders it with `renderToStaticMarkup` and asserts on the HTML,
 * without a DOM and without a stubbed global. `Interview.tsx` beside it does
 * the talking to the API.
 *
 * Three things here are requirements and not decoration:
 *
 * - **Every control carries `data-field`.** It is how `Interview.test.tsx`
 *   compares the form against the `Brief` model (AC-1). A field the model
 *   carries and the form does not is a novel written without something the
 *   buyer was never asked for, and nothing errors.
 * - **A question renders inside the block of the field it is about**, and one
 *   the map does not recognise renders at the top rather than nowhere. Wrong
 *   place beats disappeared.
 * - **`free_text` reaches no other field's value.** That is AC-3 in one
 *   sentence, and the test counts the occurrences.
 */

interface Props {
  brief: Brief
  /** null before the first answer comes back, which is not the same as `ok`. */
  check: CheckResult | null
  busy: boolean
  error: string | null
  /** What past novels cost. Null when nothing has been measured — and then the
   *  card says so in words rather than showing a zero. */
  projection?: Projection | null
  onChange: (next: Brief) => void
  onCheck: () => void
  onLoadExample: () => void
  onSubmit: () => void
}

/** Everything the check said about one field: its questions, then any
 *  contradiction that named it. Both sides of a contradiction get the sentence,
 *  because either one of the two answers may be the one to change. */
function notesFor(check: CheckResult | null, field: string): string[] {
  if (!check) return []
  return [
    ...check.questions.filter((q) => fieldOfQuestion(q) === field),
    ...check.contradictions.filter((c) => fieldsOfContradiction(c).includes(field)),
  ]
}

function Field({ field, label, hint, check, children }: {
  field: string
  label: string
  hint?: ReactNode
  check: CheckResult | null
  children: (asked: boolean) => ReactNode
}) {
  const notes = notesFor(check, field)
  return (
    <div className="field">
      <label htmlFor={field}>{label}</label>
      {children(notes.length > 0)}
      {hint && <p className="hint">{hint}</p>}
      {notes.map((note) => (
        // The word carries the meaning; the rule beside it only repeats it.
        // Colour is never the only signal (SPEC-EXAM-002 §7).
        <p className="asked-about" key={note}>
          <strong>We still need: </strong>
          {note}
        </p>
      ))}
    </div>
  )
}

function TextField({ field, label, hint, value, rows, check, onChange, onCheck }: {
  field: string
  label: string
  hint?: ReactNode
  value: string
  rows?: number
  check: CheckResult | null
  onChange: (value: string) => void
  onCheck: () => void
}) {
  return (
    <Field field={field} label={label} hint={hint} check={check}>
      {(asked) =>
        rows ? (
          <textarea
            id={field}
            data-field={field}
            className={asked ? 'asked' : undefined}
            rows={rows}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onCheck}
          />
        ) : (
          <input
            id={field}
            type="text"
            data-field={field}
            className={asked ? 'asked' : undefined}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onCheck}
          />
        )
      }
    </Field>
  )
}

/**
 * A list, edited in place, with one empty row at the end.
 *
 * The empty row is the *add* button: typing into it appends. No local state, no
 * second control to keep in step with the list, and nothing to forget to clear.
 */
function ListField({ field, label, hint, values, check, onChange, onCheck }: {
  field: string
  label: string
  hint?: ReactNode
  values: string[]
  check: CheckResult | null
  onChange: (values: string[]) => void
  onCheck: () => void
}) {
  const replace = (i: number, value: string) => {
    const next = [...values]
    if (i === values.length) next.push(value)
    else next[i] = value
    // Not filtered here: a row cleared to be retyped would vanish under the
    // cursor. `forApi` drops what is still empty when the brief is sent.
    onChange(next)
  }
  const rows = [...values, '']
  return (
    <Field field={field} label={label} hint={hint} check={check}>
      {(asked) => (
        <>
          {rows.map((value, i) => (
            <div className="row" key={i}>
              <input
                id={i === 0 ? field : `${field}-${i}`}
                type="text"
                data-field={field}
                className={asked ? 'asked' : undefined}
                value={value}
                placeholder={i === values.length ? 'Add another…' : undefined}
                onChange={(e) => replace(i, e.target.value)}
                onBlur={onCheck}
              />
              {i < values.length && (
                <button
                  type="button"
                  className="link"
                  onClick={() => onChange(values.filter((_, j) => j !== i))}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </>
      )}
    </Field>
  )
}

/**
 * The memories, each with the date the buyer may not remember.
 *
 * An absent date stays `null`. It is never today and never the epoch: the
 * temporal validator reads these, and an invented date is an invented
 * contradiction (`backend/brief/models.Memory`).
 */
function MemoriesField({ memories, check, onChange, onCheck }: {
  memories: Memory[]
  check: CheckResult | null
  onChange: (memories: Memory[]) => void
  onCheck: () => void
}) {
  const rows: Memory[] = [...memories, { text: '', date: null }]
  const patch = (i: number, over: Partial<Memory>) => {
    const next = [...memories]
    const base: Memory = next[i] ?? { text: '', date: null }
    const merged = { ...base, ...over }
    if (i === memories.length) next.push(merged)
    else next[i] = merged
    onChange(next)
  }
  return (
    <Field
      field="memories"
      label="A few moments worth putting in a story"
      hint="A place, a person, a small object. One line each — nobody is asking for an essay. The date is optional; leave it empty if you do not remember it, and we will not invent one."
      check={check}
    >
      {(asked) => (
        <>
          {rows.map((memory, i) => (
            <div className="row" key={i}>
              <input
                id={i === 0 ? 'memories' : `memories-${i}`}
                type="text"
                data-field="memories"
                className={asked ? 'asked' : undefined}
                value={memory.text}
                placeholder={i === memories.length ? 'Add a memory…' : undefined}
                onChange={(e) => patch(i, { text: e.target.value })}
                onBlur={onCheck}
              />
              <input
                type="text"
                data-field="memories"
                aria-label={`When, for memory ${i + 1} (optional)`}
                value={memory.date ?? ''}
                placeholder="2024-07"
                onChange={(e) => patch(i, { date: e.target.value.trim() || null })}
                onBlur={onCheck}
              />
            </div>
          ))}
        </>
      )}
    </Field>
  )
}

export function InterviewForm(props: Props) {
  const { brief, check, busy, error, projection, onChange, onCheck } = props
  const set = (over: Partial<Brief>) => onChange({ ...brief, ...over })
  const setRecipient = (over: Partial<Recipient>) =>
    onChange({ ...brief, recipient: { ...brief.recipient, ...over } })

  // A question the map did not recognise still has to reach the buyer: a brief
  // that can never become complete is worse than a question in the wrong place.
  const loose = (check?.questions ?? []).filter((q) => fieldOfQuestion(q) === null)
  const ready = check?.status === 'ok'
  const who = brief.recipient.alias.trim() || 'someone'

  return (
    <>
      <section className="hero">
        <p className="eyebrow eyebrow--brand">A new novel</p>
        <h1>Tell us about {who}</h1>
        <p className="lede">
          Ten minutes of answers and we write them a book. Nothing here is a test —
          the page says what is still missing as you go.
        </p>
        <ol className="steps">
          <li>The person, and the memories only they would recognise.</li>
          <li>The story, its limits, and what it must include.</li>
          <li>Before we start: check the answers, see the cost, order.</li>
        </ol>
      </section>
      <p>
        <button type="button" onClick={props.onLoadExample}>
          Fill this in with the example brief (01-hijo)
        </button>
      </p>

      {check?.status === 'invalid' && (
        <div className="panel panel--bad">
          <h2>We could not read that</h2>
          <ul className="findings">
            {check.errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {loose.length > 0 && (
        <div className="panel panel--note">
          <h2>Still to answer</h2>
          <ul className="findings">
            {loose.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </div>
      )}

      {(check?.contradictions.length ?? 0) > 0 && (
        <div className="panel panel--note">
          <h2>Two answers that do not fit together</h2>
          {check?.contradictions.map((c) => (
            <p key={c}>{c}</p>
          ))}
        </div>
      )}

      <fieldset>
        <legend>The person</legend>
        <TextField
          field="recipient.alias"
          label="What should the novel call them?"
          hint="The name the book uses. It does not have to be their legal name."
          value={brief.recipient.alias}
          check={check}
          onChange={(alias) => setRecipient({ alias })}
          onCheck={onCheck}
        />
        <Field field="recipient.age" label="How old are they?" check={check}
          hint="Their age decides what the book may contain.">
          {(asked) => (
            <input
              id="recipient.age"
              type="number"
              min={0}
              max={120}
              data-field="recipient.age"
              className={asked ? 'asked' : undefined}
              // Empty means unknown. An unknown age is unknown, not a newborn:
              // a 0 here would make every half-filled brief for an adult look
              // like a crime against a baby.
              value={brief.recipient.age ?? ''}
              onChange={(e) =>
                setRecipient({ age: e.target.value === '' ? null : Number(e.target.value) })
              }
              onBlur={onCheck}
            />
          )}
        </Field>
        <TextField
          field="recipient.pronouns"
          label="How are they referred to?"
          hint="he/him, she/her, they/them — whatever the book should use."
          value={brief.recipient.pronouns}
          check={check}
          onChange={(pronouns) => setRecipient({ pronouns })}
          onCheck={onCheck}
        />
        <ListField
          field="recipient.traits"
          label="Three to five things that are true of them"
          hint="“Collects smooth stones” beats “nice”. The story is built out of these."
          values={brief.recipient.traits}
          check={check}
          onChange={(traits) => setRecipient({ traits })}
          onCheck={onCheck}
        />
        <TextField
          field="recipient.relationship_to_buyer"
          label="What are they to you?"
          hint="A son, a wife, a father, a friend."
          value={brief.recipient.relationship_to_buyer}
          check={check}
          onChange={(relationship_to_buyer) => setRecipient({ relationship_to_buyer })}
          onCheck={onCheck}
        />
      </fieldset>

      <fieldset>
        <legend>Memories</legend>
        <MemoriesField
          memories={brief.memories}
          check={check}
          onChange={(memories) => set({ memories })}
          onCheck={onCheck}
        />
      </fieldset>

      <fieldset>
        <legend>The story</legend>
        <TextField
          field="occasion"
          label="What is the occasion?"
          hint="A birthday, an anniversary, a retirement."
          value={brief.occasion}
          check={check}
          onChange={(occasion) => set({ occasion })}
          onCheck={onCheck}
        />
        <TextField
          field="genre"
          label="What kind of story should it be?"
          hint="Children's adventure, romantic comedy, family saga…"
          value={brief.genre}
          check={check}
          onChange={(genre) => set({ genre })}
          onCheck={onCheck}
        />
        <TextField
          field="tone"
          label="And what tone?"
          hint="Warm, funny, tender, sharp."
          value={brief.tone}
          check={check}
          onChange={(tone) => set({ tone })}
          onCheck={onCheck}
        />
        <Field
          field="length_chapters"
          label="How long is it?"
          check={check}
          hint="Every storyMaker novel is ten chapters. This one is not a choice yet."
        >
          {() => (
            <input
              id="length_chapters"
              type="text"
              data-field="length_chapters"
              readOnly
              value={`${LENGTH_CHAPTERS} chapters`}
            />
          )}
        </Field>
      </fieldset>

      <fieldset>
        <legend>Limits and must-haves</legend>
        <ListField
          field="forbidden_terms"
          label="Words and subjects that must never appear"
          hint="A former partner's name, an illness, a pet that died. Every chapter is checked against this list."
          values={brief.forbidden_terms}
          check={check}
          onChange={(forbidden_terms) => set({ forbidden_terms })}
          onCheck={onCheck}
        />
        <ListField
          field="mandatory_facts"
          label="Things that must be in the book"
          hint="“The dog is called Bruno.” The finished novel is checked for each of these."
          values={brief.mandatory_facts}
          check={check}
          onChange={(mandatory_facts) => set({ mandatory_facts })}
          onCheck={onCheck}
        />
        <TextField
          field="dedication"
          label="The dedication for the first page"
          value={brief.dedication}
          rows={2}
          check={check}
          onChange={(dedication) => set({ dedication })}
          onCheck={onCheck}
        />
        <TextField
          field="free_text"
          label="Anything else — a letter, an anecdote, a note they wrote"
          rows={6}
          hint={
            <>
              <strong>We use this as material for the story. We never follow
              instructions written in it.</strong>{' '}
              Whatever is pasted here is kept whole and read as something the
              novel may draw on — never as something the system is told to do.
            </>
          }
          value={brief.free_text}
          check={check}
          onChange={(free_text) => set({ free_text })}
          onCheck={onCheck}
        />
      </fieldset>

      {error && <p className="panel panel--bad">{error}</p>}

      <div className="panel panel--note">
        <h2>Before we start</h2>
        <p>
          A {brief.genre.trim() || 'story'} for {who}
          {brief.occasion.trim() ? `, for ${brief.occasion.trim()}` : ''}, in{' '}
          {LENGTH_CHAPTERS} chapters.
        </p>
        <p className="muted">What novels like this one have cost:</p>
        {projection ? (
          <p className="figure">
            {money(projection.low)} <Provenance grade={gradeOf(projection.low)} /> ·{' '}
            {money(projection.typical)} <Provenance grade={gradeOf(projection.typical)} /> ·{' '}
            {money(projection.high)} <Provenance grade={gradeOf(projection.high)} />
          </p>
        ) : (
          // No finished novel has reported a cost to this screen yet. "$0.00"
          // would be a promise the system cannot keep, and a run that destroyed
          // its evidence and a run that cost nothing must not look the same.
          <p className="figure">
            {money(undefined)} <Provenance grade="absent" />
          </p>
        )}
        <p className="hint">
          {projection
            ? `Lowest, typical and highest of ${projection.runs} novel(s) already written. An estimate, not a price.`
            : 'No finished novel has reported a cost to this screen yet, so there is no figure to give you — which is not the same as it being free.'}
        </p>
        <button type="button" className="primary" disabled={busy || !ready} onClick={props.onSubmit}>
          {busy ? 'Starting…' : 'Write it'}
        </button>
        {!ready && (
          <p className="hint">
            The button above stays out of reach until nothing is missing and no
            two answers contradict each other. A novel costs money to write, and
            this is the last place it is free to change your mind.
          </p>
        )}
      </div>
    </>
  )
}
