import type { Run, RunDetail } from './types'

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
}

export const eventsUrl = (id: string) => `/api/runs/${id}/events`
