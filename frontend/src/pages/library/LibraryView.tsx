import type { Run } from '@/shared/api/types'
import { plainStatus, stepOf, titleOf } from '@/entities/run/status'

export type LibraryPlace = 'library' | 'bin'

/**
 * Every run, new beside imported — and, since SPEC-EXAM-007, the bin.
 *
 * Imported ones are marked and never pooled into statistics: they were judged by
 * a different set of characteristics, so a pass rate over them does not measure
 * what it claims. Evidence, not sample.
 *
 * A stopped novel offers "Continue" and "Move to bin". Stopped is the
 * server's word (`run.stopped`: units missing, no process live), not the
 * stage's — the example novel stopped at 8/10 with `stage = complete`.
 *
 * Pure: the page owns the state, this only draws it.
 */
export function LibraryView(p: {
  view: LibraryPlace
  runs: Run[]
  /** The bin, or null while it is being read. */
  binned: Run[] | null
  published: Record<string, boolean>
  /** The run whose move to the bin is waiting for its one confirmation. */
  confirming: string | null
  notice: string | null
  error: string | null
  onView: (view: LibraryPlace) => void
  onOpen: (id: string) => void
  onNew: () => void
  onContinue: (run: Run) => void
  onTrash: (run: Run) => void
  onConfirmTrash: (run: Run) => void
  onCancelTrash: () => void
  onRestore: (run: Run) => void
}) {
  const { runs, binned, published } = p
  const status = (run: Run) => plainStatus(run, run.live === true, published[run.id])
  const count = (tone: string) => runs.filter((r) => status(r).tone === tone).length
  const order = { live: 0, ok: 1, halt: 2 } as const
  const sorted = [...runs].sort((x, y) => order[status(x).tone] - order[status(y).tone])

  const tabs = (
    <nav aria-label="Library" className="tabs">
      <button
        type="button"
        className={p.view === 'library' ? 'active' : ''}
        aria-current={p.view === 'library' ? 'page' : undefined}
        onClick={() => p.onView('library')}
      >
        Your novels
      </button>
      <button
        type="button"
        className={p.view === 'bin' ? 'active' : ''}
        aria-current={p.view === 'bin' ? 'page' : undefined}
        onClick={() => p.onView('bin')}
      >
        {binned === null ? 'Bin' : `Bin (${binned.length})`}
      </button>
    </nav>
  )

  const banners = (
    <>
      {p.notice && <p className="panel panel--ok">{p.notice}</p>}
      {p.error && <p className="panel panel--bad">{p.error}</p>}
    </>
  )

  if (p.view === 'bin') {
    const inBin = binned ?? []
    return (
      <>
        <section className="hero hero--halt">
          <p className="eyebrow">Bin</p>
          <h1>{inBin.length} novel{inBin.length === 1 ? '' : 's'} in the bin</h1>
          <p className="lede">
            Nothing here was deleted. Each one’s files are kept under <code>output/_papelera/</code>,
            and "Restore" puts them back exactly as they were.
          </p>
        </section>
        {tabs}
        {banners}
        {binned === null && <p className="muted">Reading the bin…</p>}
        {binned !== null && inBin.length === 0 && <p className="panel muted">The bin is empty.</p>}
        <div className="grid grid--2">
          {inBin.map((run) => (
            <article key={run.id} data-run={run.id} className="card">
              <div className="row">
                <span className="badge badge--halt">In the bin</span>
                <span className="badge">{run.profile === 'eval' ? 'test' : run.profile}</span>
              </div>
              <h2>{titleOf(run)}</h2>
              <p className="muted clamp">{run.premise}</p>
              <div className="card__foot">
                <span className="hint">{run.id}</span>
                <button type="button" className="primary" onClick={() => p.onRestore(run)}>Restore</button>
              </div>
            </article>
          ))}
        </div>
      </>
    )
  }

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
        <button type="button" className="primary" onClick={p.onNew}>
          Order a new novel
        </button>
        <p className="hint">
          {runs.length} run{runs.length === 1 ? '' : 's'} in total;{' '}
          {runs.filter((r) => r.source === 'pre-loop003').length} imported from the
          previous implementation and kept apart from the statistics.
        </p>
      </section>

      {tabs}
      {banners}

      {runs.length === 0 && (
        <p className="panel muted">
          Nothing yet. A <code>tiny</code> run is three chapters and, on the mock
          engine, costs nothing.
        </p>
      )}

      <div className="grid grid--2">
        {sorted.map((run) => {
          const s = status(run)
          const asking = p.confirming === run.id
          return (
            <article key={run.id} data-run={run.id} className="card card--action">
              <div className="row">
                <span className={`badge badge--${s.tone}`}>{s.label}</span>
                <span className="badge">{run.profile === 'eval' ? 'test' : run.profile}</span>
                {run.source === 'pre-loop003' && <span className="badge">imported</span>}
              </div>
              <h2>{titleOf(run)}</h2>
              {s.tone === 'live' && <p className="lede">Now: {stepOf(run.stage)}</p>}
              {run.stopped && run.resume_stage && (
                <p className="hint">Stopped at: {stepOf(run.resume_stage)} ({run.resume_from})</p>
              )}
              <p className="muted clamp">{run.premise}</p>
              {run.stopped && asking && (
                <div className="confirm" role="alert">
                  <p>Move «{titleOf(run)}» to the bin?</p>
                  <p className="hint">Nothing is deleted; it can be restored from the Bin.</p>
                  <div className="card__actions">
                    <button type="button" className="primary" onClick={() => p.onConfirmTrash(run)}>Yes, move</button>
                    <button type="button" onClick={p.onCancelTrash}>Cancel</button>
                  </div>
                </div>
              )}
              <div className="card__foot">
                <span className="hint">{run.id}</span>
                <div className="card__actions">
                  {run.stopped && !asking && (
                    <>
                      <button type="button" onClick={() => p.onTrash(run)}>Move to bin</button>
                      <button type="button" onClick={() => p.onContinue(run)}>Continue</button>
                    </>
                  )}
                  <button type="button" className="primary" onClick={() => p.onOpen(run.id)}>
                    Open
                  </button>
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </>
  )
}
