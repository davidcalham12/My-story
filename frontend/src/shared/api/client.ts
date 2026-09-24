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
    const body = (await response.json().catch(() => ({}))) as { detail?: unknown }
    // FastAPI's validation errors are a list of objects; a thrown object
    // printed as "[object Object]" tells the buyer nothing.
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => (d as { msg?: string }).msg ?? JSON.stringify(d)).join('; ')
      : typeof body.detail === 'string' ? body.detail : null
    throw new Error(detail ?? `HTTP ${response.status}`)
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
   * Start the run this brief describes. The brief alone: the route composes the
   * premise from it, and refuses a request that carries both (`StartRun`).
   * Always the `exam` profile; `chapters` is the length the buyer chose, which
   * the route bounds by what that profile was priced for.
   */
  startFromBrief: (brief_id: string, chapters: number | null) =>
    json<{ id: string; slug: string }>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ brief_id, profile: 'exam', chapters }),
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
/** The same PDF as an attachment: only behind the button that asks for it. */
export const downloadUrl = (id: string, n: number) => `${pdfUrl(id, n)}?download=true`
/** The page the PDF was printed from, to read in the panel. */
export const htmlUrl = (id: string, n: number) => `/api/runs/${id}/versions/${n}/html`

export const eventsUrl = (id: string) => `/api/runs/${id}/events`
