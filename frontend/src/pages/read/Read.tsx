import { useEffect, useState } from 'react'
import { ReadView } from './ReadView'
import { changedIn, current, factOfReason } from '@/entities/version/lib'
import { api } from '@/shared/api/client'
import type {
  ChapterEntry, CharacterEntry, Impact, PlaceEntry, VersionRow,
} from '@/shared/api/types'
import type { Changed } from '@/entities/version/lib'

/**
 * *Read*, wired up. `ReadView` beside it does the rendering.
 *
 * Each call is settled on its own rather than through one `Promise.all`. The
 * index, the character sheet and the place sheet are four separate endpoints at
 * four different stages of being built, and one of them 404ing must cost its
 * own panel and not the book: the whole screen going blank because the bible
 * was never ingested is the failure this shape exists to prevent.
 */
export function Read({ runId, onAskForAChange }: {
  runId: string
  onAskForAChange: () => void
}) {
  const [versions, setVersions] = useState<VersionRow[]>([])
  const [chosen, setChosen] = useState<number | null>(null)
  const [chapters, setChapters] = useState<ChapterEntry[]>([])
  const [characters, setCharacters] = useState<CharacterEntry[]>([])
  const [places, setPlaces] = useState<PlaceEntry[]>([])
  const [changed, setChanged] = useState<Changed | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    // An endpoint that is not there yet leaves its own panel saying so. It
    // does not take the book down with it.
    const list = <T,>(set: (rows: T[]) => void) => [
      (rows: T[]) => { if (alive) set(Array.isArray(rows) ? rows : []) },
      (e: unknown) => { if (alive) { set([]); console.warn(`[read] ${String(e)}`) } },
    ] as const

    api.versions(runId).then((rows) => {
      if (!alive) return
      setVersions(rows)
      setChosen((held) => held ?? current(rows))
    }, (e) => alive && setError(String(e)))

    api.chapters(runId).then(...list(setChapters))
    api.characters(runId).then(...list(setCharacters))
    api.places(runId).then(...list(setPlaces))

    return () => { alive = false }
  }, [runId])

  // Which chapters this version rewrote. The archive stores the reason and not
  // a chapter list, so the fact named in the reason is asked what it reached —
  // the same `fact_usage` rows the regeneration itself worked from.
  useEffect(() => {
    let alive = true
    const version = versions.find((v) => v.n === chosen)
    if (!version || version.n <= 1) return setChanged(null)
    const factId = factOfReason(version.reason)
    if (!factId) return setChanged(changedIn(version, null))

    api.impact(runId, factId, (version.parent ?? version.n - 1)).then(
      (impact: Impact) => alive && setChanged(changedIn(version, impact)),
      // Not recorded, in words. An empty list would say this version changed
      // nothing, which is the one thing it certainly did not do.
      () => alive && setChanged(changedIn(version, null)),
    )
    return () => { alive = false }
  }, [runId, chosen, versions])

  return (
    <ReadView
      runId={runId}
      versions={versions}
      chosen={chosen}
      chapters={chapters}
      characters={characters}
      places={places}
      changed={changed}
      error={error}
      onChoose={setChosen}
      onAskForAChange={onAskForAChange}
    />
  )
}
