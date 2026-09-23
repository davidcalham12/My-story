import type {
  ChangePlan, ChapterEntry, CharacterEntry, CheckResult, FactRow, Impact, PlaceEntry,
  Run, RunDetail, VersionRow,
} from './types'

/** Everything the browser knows comes through here. */

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${response.status}`)
  }
  return (await response.json()) as T
}

export const api = {
  health: () => json<{ ok: boolean; engine: string }>('/api/health'),
  list: () => json<Run[]>('/api/runs'),
  detail: (id: string) => json<RunDetail>(`/api/runs/${id}`),
  start: (premise: string, profile: string, tone: string) =>
    json<{ id: string; slug: string }>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ premise, profile, tone }),
    }),

  /* --- the brief (FLOW-0) ------------------------------------------------ */

  /** Free, and callable as often as the form likes: it spends nothing and it
   *  is the only thing that may enable *Write it*. */
  checkBrief: (brief: unknown) =>
    json<CheckResult>('/api/briefs/check', { method: 'POST', body: JSON.stringify(brief) }),

  createBrief: (brief: unknown) =>
    json<{ id: string }>('/api/briefs', { method: 'POST', body: JSON.stringify(brief) }),

  briefExamples: () => json<Record<string, unknown>[]>('/api/briefs/examples'),

  /**
   * Start the run this brief describes.
   *
   * `brief_id` is what PLAN-EXAM-002 §B.3 specifies and what the route will
   * take once E2 lands. `premise` and `profile` go with it because the route as
   * it stands today requires a premise of at least ten characters and would
   * answer 422 to `{brief_id}` alone — the buyer would press the only button on
   * the screen and be told nothing. The premise is composed from the brief and
   * is what the Library shows as the novel's line.
   */
  startFromBrief: (brief_id: string, premise: string, tone: string) =>
    json<{ id: string; slug: string }>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ brief_id, premise, profile: 'exam', tone }),
    }),

  /* --- reading and changing (FLOW-6) ------------------------------------- */

  versions: (id: string) => json<VersionRow[]>(`/api/runs/${id}/versions`),
  chapters: (id: string) => json<ChapterEntry[]>(`/api/runs/${id}/chapters`),
  characters: (id: string) => json<CharacterEntry[]>(`/api/runs/${id}/bible/characters`),
  places: (id: string) => json<PlaceEntry[]>(`/api/runs/${id}/bible/places`),
  facts: (id: string, version = 1) =>
    json<FactRow[]>(`/api/runs/${id}/facts?version=${version}`),
  impact: (id: string, factId: number | string, version = 1) =>
    json<Impact>(`/api/runs/${id}/facts/${factId}/impact?version=${version}`),
  requestChange: (id: string, fact_id: number | string, to: string) =>
    json<ChangePlan>(`/api/runs/${id}/changes`, {
      method: 'POST',
      body: JSON.stringify({ fact_id: String(fact_id), to }),
    }),
}

/** The PDF, by run and version. Never by a path: no route takes one, so the
 *  traversal surface does not exist rather than being defended. */
export const pdfUrl = (id: string, n: number) => `/api/runs/${id}/versions/${n}/pdf`

export const eventsUrl = (id: string) => `/api/runs/${id}/events`
