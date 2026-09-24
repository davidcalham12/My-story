import { useEffect, useState } from 'react'
import { useRun } from '@/features/watch-progress/useRun'
import { api } from '@/shared/api/client'
import { haltReason } from '@/entities/run/lib'
import { gradeOf, money, tokens } from '@/shared/lib/provenance'
import { Provenance } from '@/shared/ui/Provenance'
import { GateTable } from '@/entities/critique/GateTable'
import { plainStatus, titleOf } from '@/entities/run/status'

/** One run, pyramid order: the answer in one sentence, the next thing to do,
 *  three figures, and the technical record folded underneath. */
export function RunPage({ runId, onRead, onChange }: {
  runId: string
  onRead?: () => void
  onChange?: () => void
}) {
  const { detail, progress, live, error } = useRun(runId)
  const [published, setPublished] = useState<boolean | undefined>(undefined)
  const finished = detail ? detail.run.stage === 'complete' || detail.run.halted !== null : false
  useEffect(() => {
    let alive = true
    if (finished) api.versions(runId).then((v) => alive && setPublished(v.length > 0), () => undefined)
    return () => { alive = false }
  }, [runId, finished])

  if (error) return <p className="panel panel--bad">{error}</p>
  if (!detail) return <p className="muted">Reading the run…</p>

  const { run, cost, warnings, completeness, conformance } = detail
  const halted = haltReason(run)
  const status = plainStatus(run, live, published)

  return (
    <>
      <section className={`hero hero--${status.tone}`}>
        <p className="eyebrow eyebrow--brand">{titleOf(run)}</p>
        <h1>{status.headline}</h1>
        <p className="lede">{status.detail}</p>
        {live && progress && <p className="hint">Last step: {progress.detail}</p>}
        <div className="row">
          {status.tone === 'ok' && onRead && (
            <button type="button" className="primary" onClick={onRead}>Read the book</button>
          )}
          {status.tone === 'ok' && onChange && (
            <button type="button" onClick={onChange}>Ask for a change</button>
          )}
        </div>
      </section>

      <div className="grid grid--3">
        <div className="stat">
          <p className="stat__label">Calls</p>
          <p className="stat__value">{cost.calls}</p>
        </div>
        <div className="stat">
          <p className="stat__label">Tokens in / out</p>
          <p className="stat__value">
            {tokens(cost.input_tokens)} / {tokens(cost.output_tokens)}{' '}
            <Provenance grade={cost.tokens_provenance} />
          </p>
        </div>
        <div className="stat">
          <p className="stat__label">Cost</p>
          <p className="stat__value">
            {money(cost)} <Provenance grade={gradeOf(cost)} />
          </p>
        </div>
      </div>

      <details className="more">
        <summary>Technical details — for the team</summary>
        <p className="hint">The order the novel was written from: {run.premise}</p>

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

      <h2 className="section">Did it obey its own gate?</h2>
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
          <div className="table-card scroll-x"><table>
            <tbody>
              {completeness.map((gap) => (
                <tr key={gap.field}>
                  <th>{gap.field}</th>
                  <td>{gap.note ?? gap.state}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </>
      )}

      {warnings.length > 0 && (
        <>
          <h2>Warnings</h2>
          {warnings.map((warning, i) => (
            <p key={i} className="panel panel--halt">
              <strong>{warning.kind}</strong>
              {warning.chapter !== null ? ` (chapter ${warning.chapter})` : ''} —{' '}
              {warning.detail}
            </p>
          ))}
        </>
      )}

      <GateTable detail={detail} />
      </details>
    </>
  )
}
