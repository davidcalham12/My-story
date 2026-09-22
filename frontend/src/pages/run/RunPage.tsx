import { useRun } from '@/features/watch-progress/useRun'
import { haltReason } from '@/entities/run/lib'
import { gradeOf, money, tokens } from '@/shared/lib/provenance'
import { Provenance } from '@/shared/ui/Provenance'
import { Quality } from '@/pages/quality/Quality'

/** One run: what it is doing, what it cost, and how its gate behaved. */
export function RunPage({ runId }: { runId: string }) {
  const { detail, progress, live, error } = useRun(runId)

  if (error) return <p className="panel panel--bad">{error}</p>
  if (!detail) return <p className="muted">Reading the run…</p>

  const { run, cost, warnings, completeness, conformance } = detail
  const halted = haltReason(run)

  return (
    <>
      <h1>{run.slug}</h1>
      <p className="lede">{run.premise}</p>

      {live && (
        <p className="panel">
          <strong>Running.</strong>{' '}
          {progress ? `${progress.stage} — ${progress.detail}` : 'starting'}
        </p>
      )}

      {halted && (
        <div className="panel panel--halt">
          <h2>This run stopped: {run.halted}</h2>
          <p>{halted}</p>
          {run.halted_detail && <pre className="code">{run.halted_detail}</pre>}
          <p className="muted">
            Everything it produced before stopping is here and readable. A chapter
            that failed the gate was <em>not</em> put in the book with a note in
            the margin — that exit no longer exists.
          </p>
        </div>
      )}

      <h2>Did it obey its own gate?</h2>
      <p className={`panel panel--${conformance.verdict === 'breached' ? 'bad' : 'ok'}`}>
        {conformance.verdict === 'conformant' && (
          <>
            <strong>Yes.</strong> {conformance.attempts_checked} attempts checked
            against the rule in <code>decide()</code>, recomputed from the archive
            rather than taken on trust. No draft below the threshold was promoted.
          </>
        )}
        {conformance.verdict === 'breached' && (
          <>
            <strong>No — and this is the one thing on this page worth acting on.</strong>{' '}
            The record contradicts the rule the gate is supposed to follow.
          </>
        )}
        {conformance.verdict === 'unchecked' && (
          <>
            <strong>Not checked.</strong> Nothing with a score to judge. That is
            not the same as obedient — it means the question has no answer here.
          </>
        )}
        {conformance.verdict === 'not_applicable' && (
          <>
            <strong>Not applicable.</strong> {conformance.why ?? ''} Judging it by
            today's rule would produce a confident answer about nothing.
          </>
        )}
      </p>
      {conformance.breaches.length > 0 && (
        <ul className="findings">
          {conformance.breaches.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      )}
      {conformance.unjudgeable > 0 && (
        <p className="hint">
          {conformance.unjudgeable} attempt(s) had no usable score and could not be
          judged either way. Unjudgeable is not clean.
        </p>
      )}

      <h2>What it cost</h2>
      <table>
        <tbody>
          <tr>
            <th>calls</th>
            <td className="num">{cost.calls}</td>
          </tr>
          <tr>
            <th>tokens in / out</th>
            <td className="num">
              {tokens(cost.input_tokens)} / {tokens(cost.output_tokens)}{' '}
              <Provenance grade={cost.tokens_provenance} />
            </td>
          </tr>
          <tr>
            <th>cost</th>
            <td className="num">
              {money(cost)} <Provenance grade={gradeOf(cost)} />
            </td>
          </tr>
        </tbody>
      </table>
      {cost.provenance.includes('reconstructed') && (
        <p className="hint">
          Some figures were rebuilt afterwards from what survived. An imported run
          recorded one token total with no split, so its halves stay absent rather
          than being invented.
        </p>
      )}

      {completeness.length > 0 && (
        <>
          <h2>What this run did not record</h2>
          <p className="hint">
            A gap reads as a gap. A run that never wrote gate rows must not
            resemble one whose gate passed everything first time.
          </p>
          <table>
            <tbody>
              {completeness.map((gap) => (
                <tr key={gap.field}>
                  <th>{gap.field}</th>
                  <td>{gap.note ?? gap.state}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {warnings.length > 0 && (
        <>
          <h2>Warnings</h2>
          {warnings.map((warning, i) => (
            <p key={i} className="panel">
              <strong>{warning.kind}</strong>
              {warning.chapter !== null ? ` (chapter ${warning.chapter})` : ''} —{' '}
              {warning.detail}
            </p>
          ))}
        </>
      )}

      <Quality detail={detail} />
    </>
  )
}
