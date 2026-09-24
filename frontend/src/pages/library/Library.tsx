import { useCallback, useEffect, useState } from 'react'
import { api } from '@/shared/api/client'
import type { Run } from '@/shared/api/types'
import { titleOf } from '@/entities/run/status'
import { ContinueDialog } from './ContinueDialog'
import { LibraryView, type LibraryPlace } from './LibraryView'

/**
 * The library's state: the runs, the bin, and what the owner is in the middle
 * of doing to one of them. Everything it draws is `LibraryView` and
 * `ContinueDialog`, which are pure and tested (SPEC-EXAM-007 AC-6).
 */
export function Library({ onOpen, onNew }: {
  onOpen: (id: string) => void
  onNew: () => void
}) {
  const [runs, setRuns] = useState<Run[] | null>(null)
  const [binned, setBinned] = useState<Run[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  // Which runs actually published a book: a "complete" row is not proof there
  // is anything to read, and a stopped one may still have published.
  const [published, setPublished] = useState<Record<string, boolean>>({})
  const [view, setView] = useState<LibraryPlace>('library')
  const [confirming, setConfirming] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  // The continuation being prepared, and what has been typed for it.
  const [continuing, setContinuing] = useState<Run | null>(null)
  const [ceiling, setCeiling] = useState('')
  const [busy, setBusy] = useState(false)
  const [dialogError, setDialogError] = useState<string | null>(null)

  const load = useCallback((alive: () => boolean = () => true) => {
    api.list().then(
      (r) => {
        if (!alive()) return
        setRuns(r)
        r.forEach((run) =>
          api.versions(run.id).then(
            (v) => alive() && setPublished((p) => ({ ...p, [run.id]: v.length > 0 })),
            () => undefined,
          ),
        )
      },
      (e) => alive() && setLoadError(String(e)),
    )
    // An older server has no bin; the library still works without it.
    api.bin().then((b) => alive() && setBinned(b), () => alive() && setBinned([]))
  }, [])

  useEffect(() => {
    let alive = true
    load(() => alive)
    return () => {
      alive = false
    }
  }, [load])

  if (loadError) return <p className="panel panel--bad">{loadError}</p>
  if (!runs) return <p className="muted">Reading the library…</p>

  /** A bin move: the reason on screen when refused, the lists re-read when not. */
  const act = (what: Promise<unknown>, done: string) => {
    setError(null)
    setNotice(null)
    what.then(
      () => {
        setNotice(done)
        load()
      },
      (e) => setError(e instanceof Error ? e.message : String(e)),
    )
  }

  const confirmContinue = () => {
    if (!continuing) return
    setBusy(true)
    setDialogError(null)
    api.resume(continuing.id, continuing.asks_for_figure ? Number(ceiling) : null).then(
      () => {
        setBusy(false)
        setContinuing(null)
        onOpen(continuing.id)
      },
      (e) => {
        setBusy(false)
        setDialogError(e instanceof Error ? e.message : String(e))
      },
    )
  }

  return (
    <>
      <LibraryView
        view={view}
        runs={runs}
        binned={binned}
        published={published}
        confirming={confirming}
        notice={notice}
        error={error}
        onView={(v) => {
          setView(v)
          setConfirming(null)
        }}
        onOpen={onOpen}
        onNew={onNew}
        onContinue={(run) => {
          setContinuing(run)
          setCeiling('')
          setDialogError(null)
        }}
        onTrash={(run) => setConfirming(run.id)}
        onCancelTrash={() => setConfirming(null)}
        onConfirmTrash={(run) => {
          setConfirming(null)
          act(api.trash(run.id), `«${titleOf(run)}» is in the Papelera. Nothing was deleted.`)
        }}
        onRestore={(run) => act(api.restore(run.id), `«${titleOf(run)}» is back in the library.`)}
      />
      {continuing && (
        <ContinueDialog
          run={continuing}
          ceiling={ceiling}
          busy={busy}
          error={dialogError}
          onCeiling={setCeiling}
          onConfirm={confirmContinue}
          onCancel={() => setContinuing(null)}
        />
      )}
    </>
  )
}
