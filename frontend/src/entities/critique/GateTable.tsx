import { CHARACTERISTICS, type Attempt, type Characteristic, type RunDetail } from '@/shared/api/types'
import { THRESHOLD, bestAttempt, chapters, unscored, worst } from './lib'

/**
 * Typed against `Characteristic`, not `string`.
 *
 * As `Record<string, string>` a missing entry returned `undefined` and the
 * column header rendered empty — which is how SPEC-006's `prose` column would
 * have shipped nameless. The compiler refuses an incomplete map now, so the next
 * characteristic cannot be added without naming it here.
 */
const LABEL: Record<Characteristic, string> = {
  continuity: 'Continuity',
  science: 'Science',
  outline: 'Outline',
  length: 'Length',
  chatter: 'Heading',
  prose: 'Prose',
}

function Score({ attempt, which }: { attempt: Attempt; which: string }) {
  const value = attempt.scores[which as keyof typeof attempt.scores]
  if (value === null || value === undefined) {
    return (
      <span
        className="score score--none"
        title="no usable verdict — EXCLUDED from the minimum, never counted as a pass"
      >
        —
      </span>
    )
  }
  return (
    <span className={`score${value < THRESHOLD ? ' score--fail' : ''}`}>{value}</span>
  )
}

/**
 * The gate, attempt by attempt.
 *
 * Five characteristics, aggregated with `min`: a chapter is worth what its worst
 * characteristic is worth. Two of the five are arithmetic and reproduce; three
 * are a model's judgement and do not — so "it passed the gate" is a statement
 * about one run and not a property of the text.
 *
 * It lives in `entities/` and not in `pages/quality` because two pages need it.
 * While it was a page, `pages/run` imported `pages/quality` — sideways, which
 * FSD forbids — and the cost was real: deleting the Quality page would have
 * broken the Run page, and nothing that was not already a page could show the
 * table. `identity.test.ts` now fails the build on the next sideways import.
 */
export function GateTable({ detail }: { detail: RunDetail }) {
  const { attempts, run } = detail

  if (!attempts.length) {
    return (
      <>
        <h2>The gate</h2>
        <p className="panel muted">
          No attempts recorded. Either the run stopped before FLOW-4, or it is
          still writing.
        </p>
      </>
    )
  }

  return (
    <>
      <h2>The gate</h2>
      <p className="hint">
        All {CHARACTERISTICS.length} must reach {THRESHOLD}; they aggregate with{' '}
        <code>min</code>.
        {run.source === 'pre-loop003' && (
          <>
            {' '}This run predates this gate, so missing columns
            mean the characteristic did not exist — not that it scored nothing.
          </>
        )}
      </p>

      <div className="scroll-x">
        <table>
          <thead>
            <tr>
              <th>ch</th>
              <th>att</th>
              {CHARACTERISTICS.map((c) => (
                <th key={c}>{LABEL[c]}</th>
              ))}
              <th>min</th>
              <th>verdict</th>
            </tr>
          </thead>
          <tbody>
            {attempts.map((attempt) => (
              <tr key={`${attempt.chapter}-${attempt.attempt}`}>
                <td className="num">{attempt.chapter}</td>
                <td className="num">{attempt.attempt}</td>
                {CHARACTERISTICS.map((c) => (
                  <td key={c} className="num">
                    <Score attempt={attempt} which={c} />
                  </td>
                ))}
                <td className="num">{attempt.aggregate ?? '—'}</td>
                <td>
                  {attempt.promoted ? 'shipped' : (attempt.verdict ?? '—')}
                  {worst(attempt).length > 0 && !attempt.promoted && (
                    <span className="muted"> ({worst(attempt).join(', ')})</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {attempts.some((a) => unscored(a).length > 0) && (
        <p className="hint">
          A dash is a critic that returned no usable verdict. It was excluded from
          the minimum rather than counted — 10 would invent an approval and 0 a
          rejection, and returning 10 here once let a malformed reply pass a draft
          silently.
        </p>
      )}

      <h2>Which draft shipped</h2>
      <div className="scroll-x">
        <table>
          <thead>
            <tr>
              <th>chapter</th>
              <th>attempts</th>
              <th>best</th>
              <th>shipped</th>
            </tr>
          </thead>
          <tbody>
            {chapters(attempts).map((n) => {
              const mine = attempts.filter((a) => a.chapter === n)
              const best = bestAttempt(attempts, n)
              const shipped = mine.find((a) => a.promoted)
              return (
                <tr key={n}>
                  <td className="num">{n}</td>
                  <td className="num">{mine.length}</td>
                  <td className="num">
                    {best ? `#${best.attempt} at ${best.aggregate ?? '—'}` : '—'}
                  </td>
                  <td className="num">
                    {shipped ? `#${shipped.attempt}` : <em>none — not in the book</em>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="hint">
        The best draft is not always the one that shipped: an accepted draft is the
        one that passed, and a chapter scoring 7 then 4 keeps the 7.
      </p>
    </>
  )
}
