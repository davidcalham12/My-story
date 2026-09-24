import type { FactRow, Impact } from '@/shared/api/types'
import { breaksLimits, listChapters } from '@/entities/fact/lib'

/**
 * One detail corrected, with the cost shown before it is paid.
 *
 * Everything the screen shows is a prop, so the test renders it to a string.
 * `AskForAChange.tsx` beside it fetches.
 *
 * The thing this screen exists for is the paragraph between the new wording and
 * the button: **which chapters would be rewritten**. A reader who presses a
 * button not knowing that has not consented to anything, and the answer is free
 * to compute — it is the same `fact_usage` rows the regeneration itself works
 * from.
 */

export interface Outcome {
  status: string
  version: number
  chapters: number[]
  why: string | null
}

interface Props {
  facts: FactRow[]
  chosenId: number | null
  to: string
  impact: Impact | null
  /** The limits the buyer set on this novel. Checked here, before anything is
   *  spent, because after is a model paid to write the word they asked us never
   *  to use. */
  forbidden: string[]
  outcome: Outcome | null
  busy: boolean
  error: string | null
  onChoose: (id: number) => void
  onTo: (value: string) => void
  onSubmit: () => void
}

export function ChangeView(props: Props) {
  const { facts, chosenId, to, impact, forbidden, outcome, busy, error } = props
  const chosen = facts.find((f) => f.id === chosenId) ?? null
  const broken = breaksLimits(to, forbidden)
  // The backend answers 409 for a fact no chapter is recorded against. Saying
  // it here means the buyer reads a sentence rather than a failed request.
  const unused = chosen !== null && impact !== null && impact.chapters.length === 0
  const ready = chosen !== null && to.trim() !== '' && broken.length === 0 && !unused

  return (
    <>
      <section className="hero">
        <p className="eyebrow eyebrow--brand">Ask for a change</p>
        <h1>Something in the book is wrong</h1>
        <p className="lede">
          Pick the detail, tell us what it should say, and we will show you exactly which
          chapters that touches before anything is written.
        </p>
        <ol className="steps">
          <li>Pick the detail that is wrong.</li>
          <li>Write what it should say.</li>
          <li>See which chapters change, then confirm.</li>
        </ol>
      </section>

      {error && <p className="panel panel--bad">{error}</p>}

      <div className="split">
        <section>
          <h2>What the story relies on</h2>
          {facts.length === 0 ? (
            <div className="panel panel--halt">
              <p><strong>No facts were recorded for this novel, so there is nothing here to correct.</strong></p>
              <p className="muted">
                A change works on the details the book was built from. They are recorded when a
                novel is ordered through <em>New novel</em> and linked to chapters when it is
                published. Open a novel ordered that way, or wait until this one is published.
              </p>
            </div>
          ) : (
            <ul className="choices">
              {facts.map((fact) => (
                <li key={fact.id} data-fact={fact.id}>
                  <button
                    type="button"
                    className="choice"
                    aria-pressed={fact.id === chosenId}
                    onClick={() => props.onChoose(fact.id)}
                  >
                    <span className="choice__text">{fact.text}</span>
                    <span className="hint">
                      {fact.source === 'freetext'
                        ? // Same table, different trust: a freetext row is a lead for
                          // a human, never a promise the publish gate checks for.
                          'From what you pasted — material for the story, not something we promised to include. '
                        : 'Something the finished book is checked for. '}
                      {fact.chapters.length > 0
                        ? `Used in ${listChapters(fact.chapters)}.`
                        : 'Which chapters use it was not recorded.'}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="split__side">
      {!chosen && facts.length > 0 && (
        <div className="panel">
          <h2>Change it to</h2>
          <p className="muted">Choose a detail on the list to correct it here.</p>
        </div>
      )}

      {chosen && (
        <div className="panel panel--note">
          <h2>Change it to</h2>
          <p className="verbatim muted">Now: {chosen.text}</p>
          <div className="field">
            <label htmlFor="to">What should it say instead?</label>
            <input
              id="to"
              type="text"
              value={to}
              placeholder="The dog is called Nala"
              onChange={(e) => props.onTo(e.target.value)}
            />
          </div>

          {broken.length > 0 && (
            <p className="panel panel--bad">
              That wording uses {broken.map((w) => `“${w}”`).join(' and ')} — a word you{' '}
              <strong>asked us never to</strong> put in this book. Nothing has been written
              and nothing has been spent; change the wording and the button comes back.
            </p>
          )}

          {unused && (
            <p className="panel panel--halt">
              <strong>No chapter</strong> is recorded as using this fact, so there is nothing
              to rewrite. Either it never reached the book, or its use was never written
              down — and neither is a reason to regenerate a chapter.
            </p>
          )}

          {impact && impact.chapters.length > 0 && (
            <>
              <p>
                <strong>{listChapters(impact.chapters)} would be rewritten.</strong> Nothing
                else moves: every other chapter stays word for word what it is, and the
                version you already have will still be there afterwards.
              </p>
              <p className="hint">
                Those are the chapters whose text mentions this detail. A{' '}
                <strong>paraphrase</strong> is missed rather than invented, so this list is
                the fewest chapters that would change, not necessarily all of them.
              </p>
            </>
          )}

          <button type="button" className="primary" disabled={busy || !ready} onClick={props.onSubmit}>
            {busy ? 'Asking…' : 'Request change'}
          </button>
        </div>
      )}

      {outcome && outcome.status !== 'halted' && (
        <div className="panel panel--ok">
          <h2>Asked for</h2>
          <p>
            The corrected book will be <strong>version {outcome.version}</strong>, with{' '}
            {listChapters(outcome.chapters)} written again. The version you have now stays
            exactly as it is and stays open in <em>Read</em>.
          </p>
        </div>
      )}

      {outcome && outcome.status === 'halted' && (
        <div className="panel panel--halt">
          <h2>We could not finish that change</h2>
          <p>{outcome.why ?? 'The rewrite did not pass its checks.'}</p>
          <p>
            Nothing was published: version {outcome.version - 1} <strong>stays the one you
            have</strong>, complete and unchanged. You can try a{' '}
            <strong>different wording</strong> — sometimes a shorter one goes through.
          </p>
        </div>
      )}
        </aside>
      </div>
    </>
  )
}
