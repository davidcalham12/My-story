import { useEffect, useState } from 'react'
import { ChangeView, type Outcome } from './ChangeView'
import { api } from '@/shared/api/client'
import type { FactRow, Impact } from '@/shared/api/types'

/**
 * *Ask for a change*, wired up. `ChangeView` beside it does the rendering.
 *
 * The impact is fetched the moment a fact is picked and **before** the new
 * wording matters, because it is what the buyer is being asked to consent to
 * and it costs nothing to compute: the same `fact_usage` rows the regeneration
 * itself would work from.
 *
 * `forbidden` is a prop with an empty default, and that is a known gap rather
 * than an oversight: no route yet returns the brief a run was started from, so
 * the limits the buyer set are not reachable from here. The check itself is
 * written and tested (`entities/fact/lib.ts`, criterion 6); it starts working
 * the day a run can be asked for its brief.
 */
export function AskForAChange({ runId, version = 1, forbidden = [], onVersion }: {
  runId: string
  version?: number
  forbidden?: string[]
  onVersion: (n: number) => void
}) {
  const [facts, setFacts] = useState<FactRow[]>([])
  const [chosenId, setChosenId] = useState<number | null>(null)
  const [to, setTo] = useState('')
  const [impact, setImpact] = useState<Impact | null>(null)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    api.facts(runId, version).then(
      (rows) => alive && setFacts(rows),
      (e) => alive && setError(String(e)),
    )
    return () => { alive = false }
  }, [runId, version])

  useEffect(() => {
    let alive = true
    setImpact(null)
    if (chosenId === null) return
    api.impact(runId, chosenId, version).then(
      (i) => alive && setImpact(i),
      (e) => alive && setError(String(e)),
    )
    return () => { alive = false }
  }, [runId, version, chosenId])

  const submit = async () => {
    if (chosenId === null) return
    setBusy(true)
    setError(null)
    try {
      const plan = await api.requestChange(runId, chosenId, to)
      setOutcome({
        status: plan.status,
        version: plan.version,
        chapters: plan.chapters,
        why: null,
      })
      // The new version is the one to open. The previous one stays selectable
      // in *Read*: no action deletes a version the buyer already received.
      if (plan.status !== 'halted') onVersion(plan.version)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <ChangeView
      facts={facts}
      chosenId={chosenId}
      to={to}
      impact={impact}
      forbidden={forbidden}
      outcome={outcome}
      busy={busy}
      error={error}
      onChoose={(id) => { setChosenId(id); setOutcome(null) }}
      onTo={setTo}
      onSubmit={submit}
    />
  )
}
