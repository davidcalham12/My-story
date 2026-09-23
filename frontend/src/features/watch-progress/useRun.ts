import { useEffect, useState } from 'react'
import { api, eventsUrl } from '@/shared/api/client'
import type { RunDetail } from '@/shared/api/types'

export interface Progress {
  stage: string
  detail: string
  chapter: number | null
}

/**
 * Follows a run: the snapshot first, then live events.
 *
 * The snapshot is what makes a reconnection safe — the client never accumulates,
 * so it cannot end up holding half a state. `EventSource` reconnects on its own,
 * which is why `onerror` does not close it: doing that turns a recoverable blip
 * into a permanent failure.
 */
export function useRun(runId: string | null) {
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [progress, setProgress] = useState<Progress | null>(null)
  const [live, setLive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!runId) return
    let alive = true

    api
      .detail(runId)
      .then((d) => alive && setDetail(d))
      .catch((e) => alive && setError(String(e)))

    const source = new EventSource(eventsUrl(runId))
    setLive(true)

    source.addEventListener('snapshot', (event) => {
      if (alive) setDetail(JSON.parse((event as MessageEvent).data) as RunDetail)
    })
    source.addEventListener('progress', (event) => {
      if (alive) setProgress(JSON.parse((event as MessageEvent).data) as Progress)
    })
    source.addEventListener('done', (event) => {
      if (!alive) return
      // The stream is a view. What it ends with is confirmed against the record.
      // A `done` without `run` is not a detail (SPEC-010 W1): keep the snapshot
      // already held rather than replace it with two words.
      const final = JSON.parse((event as MessageEvent).data) as Partial<RunDetail>
      if (final.run) setDetail(final as RunDetail)
      else console.warn('done frame without run detail; keeping the snapshot', final)
      setLive(false)
      source.close()
    })

    return () => {
      alive = false
      source.close()
    }
  }, [runId])

  return { detail, progress, live, error }
}
