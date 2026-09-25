import { useEffect, useState } from 'react'
import { fetchCosts } from '@/entities/cost/api'
import { family, minutes, usd, what, when } from '@/entities/cost/lib'
import type { ChangeCost, RunCosts } from '@/entities/cost/model'
import { Provenance } from '@/shared/ui/Provenance'

/** SPEC-EXAM-008 §5: what each change to this novel cost, as Langfuse records it. */
export function CostsSection({ runId }: { runId: string }) {
  const [costs, setCosts] = useState<RunCosts | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    fetchCosts(runId).then((c) => alive && setCosts(c), (e) => alive && setError(String(e)))
    return () => { alive = false }
  }, [runId])
  return <CostsView costs={costs} error={error} />
}

const LANGFUSE: Record<string, string> = {
  ok: 'Figures as Langfuse records them, where it has the change.',
  unreachable: 'Langfuse did not answer: these are the local record, unconfirmed in Langfuse.',
  'not configured': 'Langfuse is not configured here: these are the local record, unconfirmed in Langfuse.',
  'not asked': '',
}

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many)

function Role({ model, value, none }: { model: string | null; value: number | null; none?: boolean }) {
  if (none) return <>no orchestrator (python loop)</>
  return <>{model && <span title={model}>{family(model)} </span>}{usd(value)}</>
}

function Source({ row }: { row: ChangeCost }) {
  if (row.source === 'langfuse') return <>Langfuse ✓</>
  if (row.source === 'both' && row.disagreement) {
    return (
      <>
        Langfuse and local disagree: local {usd(row.disagreement.local.total_usd)} / Langfuse{' '}
        {usd(row.disagreement.langfuse.total_usd)}
      </>
    )
  }
  return <>local — {row.status}</>
}

/** Pure: the section owns the fetch, this only draws it. Absent is a word, never $0. */
export function CostsView({ costs, error }: { costs: RunCosts | null; error: string | null }) {
  return (
    <section aria-label="Costs">
      <h2 className="section">Costs</h2>
      {error && <p className="panel panel--bad">The costs could not be read: {error}</p>}
      {!error && !costs && <p className="muted">Reading the costs…</p>}
      {costs && LANGFUSE[costs.langfuse] && <p className="hint">{LANGFUSE[costs.langfuse]}</p>}
      {costs && costs.rows.length === 0 && (
        <p className="panel muted">No change to this novel has a cost record yet.</p>
      )}
      {costs && costs.rows.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>What</th><th>When</th><th>Minutes</th><th>Total</th>
              <th>Orchestrator</th><th>Agents</th><th>Source</th><th>Trace</th>
            </tr>
          </thead>
          <tbody>
            {costs.rows.map((row) => (
              <tr key={row.n}>
                <td>
                  {what(row)}
                  {row.incomplete > 0 && (
                    <div className="hint">
                      incomplete: {row.incomplete} {plural(row.incomplete, 'process', 'processes')} without a result
                    </div>
                  )}
                  {row.total_usd === null && row.note && <div className="hint">{row.note}</div>}
                </td>
                <td>{when(row.started_at)}</td>
                <td>{minutes(row.minutes)}</td>
                <td>{usd(row.total_usd)} {row.provenance && <Provenance grade={row.provenance} />}</td>
                <td>
                  <Role model={row.orchestrator_model} value={row.orchestrator_usd}
                    none={row.no_orchestrator && row.orchestrator_model === null} />
                </td>
                <td><Role model={row.agents_model} value={row.agents_usd} /></td>
                <td><Source row={row} /></td>
                <td>
                  {row.trace_url
                    ? <a href={row.trace_url} target="_blank" rel="noreferrer">trace</a>
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th colSpan={3}>Novel total</th>
              <th>{usd(costs.total.usd)} <Provenance grade={costs.total.provenance} /></th>
              <td colSpan={4} className="hint">
                {costs.total.absent > 0 &&
                  `${costs.total.absent} ${plural(costs.total.absent, 'change', 'changes')} not measured (not counted as 0) · `}
                source: {costs.total.source}
              </td>
            </tr>
          </tfoot>
        </table>
      )}
    </section>
  )
}
