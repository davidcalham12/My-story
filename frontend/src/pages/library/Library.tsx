import { useEffect, useState } from 'react'
import { api } from '@/shared/api/client'
import type { Run } from '@/shared/api/types'

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

  useEffect(() => {
    let alive = true
    api.list().then(
      (r) => alive && setRuns(r),
      (e) => alive && setError(String(e)),
    )
    return () => {
      alive = false
    }
  }, [])

  if (error) return <p className="panel panel--bad">{error}</p>
  if (!runs) return <p className="muted">Reading the library…</p>

  return (
    <>
      <h1>The library</h1>
      <p className="lede">
        {runs.length} run{runs.length === 1 ? '' : 's'}.{' '}
        {runs.filter((r) => r.source === 'pre-loop003').length} imported from the
        previous implementation and kept apart from the statistics.
      </p>
      <p>
        <button type="button" className="primary" onClick={onNew}>
          Write a new one
        </button>
      </p>

      {runs.length === 0 && (
        <p className="panel muted">
          Nothing yet. A <code>tiny</code> run is three chapters and, on the mock
          engine, costs nothing.
        </p>
      )}

      {runs.map((run) => (
        <article key={run.id} className={`panel${run.halted ? ' panel--halt' : ''}`}>
          <h2>{run.slug}</h2>
          <p className="muted">{run.premise}</p>
          <p className="muted">
            {run.profile} · {run.stage}
            {run.halted && <> · <strong>halted: {run.halted}</strong></>}
            {run.source === 'pre-loop003' && <> · imported</>}
          </p>
          <button type="button" onClick={() => onOpen(run.id)}>
            Open
          </button>
        </article>
      ))}
    </>
  )
}
