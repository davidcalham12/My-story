import { useEffect, useState } from 'react'
import { api } from '@/shared/api/client'
import type { Run } from '@/shared/api/types'
import { plainStatus, stepOf, titleOf } from '@/entities/run/status'

/**
 * Every run, new beside imported.
 *
 * Imported ones are marked and never pooled into statistics: they were judged by
 * a different set of characteristics, so a pass rate over them does not measure
 * what it claims. Evidence, not sample.
 */
export function Library({ onOpen, onNew }: {
  onOpen: (id: string) => void
  onNew: () => void
}) {
  const [runs, setRuns] = useState<Run[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Which runs actually published a book: a "complete" row is not proof there
  // is anything to read, and a stopped one may still have published.
  const [published, setPublished] = useState<Record<string, boolean>>({})

  useEffect(() => {
    let alive = true
    api.list().then(
      (r) => {
        if (!alive) return
        setRuns(r)
        r.forEach((run) =>
          api.versions(run.id).then(
            (v) => alive && setPublished((p) => ({ ...p, [run.id]: v.length > 0 })),
            () => undefined,
          ),
        )
      },
      (e) => alive && setError(String(e)),
    )
    return () => {
      alive = false
    }
  }, [])

  if (error) return <p className="panel panel--bad">{error}</p>
  if (!runs) return <p className="muted">Reading the library…</p>

  const status = (run: Run) => plainStatus(run, false, published[run.id])
  const count = (tone: string) => runs.filter((r) => status(r).tone === tone).length
  const order = { live: 0, ok: 1, halt: 2 } as const
  const sorted = [...runs].sort((x, y) => order[status(x).tone] - order[status(y).tone])

  return (
    <>
      <section className="hero">
        <p className="eyebrow eyebrow--brand">Your novels</p>
        <h1>
          {count('live')} being written · {count('ok')} ready · {count('halt')} stopped
        </h1>
        <p className="lede">
          Each novel is a personalised gift in ten chapters. Open one to follow it, read
          it, or correct a detail.
        </p>
        <button type="button" className="primary" onClick={onNew}>
          Order a new novel
        </button>
        <p className="hint">
          {runs.length} run{runs.length === 1 ? '' : 's'} in total;{' '}
          {runs.filter((r) => r.source === 'pre-loop003').length} imported from the
          previous implementation and kept apart from the statistics.
        </p>
      </section>

      {runs.length === 0 && (
        <p className="panel muted">
          Nothing yet. A <code>tiny</code> run is three chapters and, on the mock
          engine, costs nothing.
        </p>
      )}

      <div className="grid grid--2">
        {sorted.map((run) => {
          const s = status(run)
          return (
            <article key={run.id} className="card card--action">
              <div className="row">
                <span className={`badge badge--${s.tone}`}>{s.label}</span>
                <span className="badge">{run.profile === 'eval' ? 'test' : run.profile}</span>
                {run.source === 'pre-loop003' && <span className="badge">imported</span>}
              </div>
              <h2>{titleOf(run)}</h2>
              {s.tone === 'live' && <p className="lede">Now: {stepOf(run.stage)}</p>}
              <p className="muted clamp">{run.premise}</p>
              <div className="card__foot">
                <span className="hint">{run.id}</span>
                <button type="button" className="primary" onClick={() => onOpen(run.id)}>
                  Open
                </button>
              </div>
            </article>
          )
        })}
      </div>
    </>
  )
}
