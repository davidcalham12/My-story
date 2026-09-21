import { useRun } from '@/features/watch-progress/useRun'
import { haltReason } from '@/entities/run/lib'
import { gradeOf, money } from '@/shared/lib/provenance'
import { Provenance } from '@/shared/ui/Provenance'
import { Quality } from '@/pages/quality/Quality'

/** One run: what it is doing, what it cost, and how its gate behaved. */
export function RunPage({ runId }: { runId: string }) {
  const { detail, progress, live, error } = useRun(runId)

  if (error) return <p className="panel panel--bad">{error}</p>
  if (!detail) return <p className="muted">Reading the run…</p>

  const { run, cost, warnings, completeness } = detail
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
              {cost.input_tokens.toLocaleString()} / {cost.output_tokens.toLocaleString()}
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
              {warning.chapter ? ` (chapter ${warning.chapter})` : ''} — {warning.detail}
            </p>
          ))}
        </>
      )}

      <Quality detail={detail} />
    </>
  )
}
