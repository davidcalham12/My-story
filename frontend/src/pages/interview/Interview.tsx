import { useCallback, useEffect, useState } from 'react'
import { InterviewForm } from './InterviewForm'
import { emptyBrief, forApi, fromExample } from '@/entities/brief/model'
import { api } from '@/shared/api/client'
import type { Brief, CheckResult } from '@/shared/api/types'

/**
 * The interview, wired to the backend.
 *
 * All the rendering is in `InterviewForm`, which takes the answers as props;
 * this half holds the state and does the talking, so the form can be rendered
 * to a string in a test without a DOM and without a stubbed `fetch`.
 *
 * The check is asked on blur rather than on every keystroke: it is free, but a
 * request per character arrives out of order, and a question that appears and
 * disappears as the buyer types is worse than one that appears when they stop.
 */
export function Interview({ onStarted }: { onStarted: (runId: string) => void }) {
  const [brief, setBrief] = useState<Brief>(emptyBrief)
  const [check, setCheck] = useState<CheckResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ask = useCallback((what: Brief) => {
    api.checkBrief(forApi(what)).then(setCheck, (e) =>
      // The typed answers are not lost when the check cannot be reached: this
      // sets an error and nothing else. SPEC-EXAM-002 §4.2, "States".
      setError(`We could not check the brief just now (${String(e)}). Nothing you typed is lost.`),
    )
  }, [])

  // Once on arrival, so an empty form already shows what it will need.
  useEffect(() => ask(emptyBrief()), [ask])

  const loadExample = async () => {
    setError(null)
    try {
      const examples = await api.briefExamples()
      const first = examples.find((e) => String(e.id).startsWith('01')) ?? examples[0]
      if (!first) return setError('The example briefs could not be read.')
      const filled = fromExample(first)
      setBrief(filled)
      ask(filled)
    } catch (e) {
      setError(String(e))
    }
  }

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      const { id: briefId } = await api.createBrief(forApi(brief))
      const { id } = await api.startFromBrief(briefId, brief.length_chapters ?? null)
      onStarted(id)
    } catch (e) {
      const text = e instanceof Error ? e.message : String(e)
      setError(/already in flight/.test(text)
        ? 'Another novel is being written right now, and only one is written at a time. Your answers stay on this page: order again when it finishes.'
        : text)
      setBusy(false)
    }
  }

  return (
    <InterviewForm
      brief={brief}
      check={check}
      busy={busy}
      error={error}
      onChange={setBrief}
      onCheck={() => ask(brief)}
      onLoadExample={loadExample}
      onSubmit={submit}
    />
  )
}
