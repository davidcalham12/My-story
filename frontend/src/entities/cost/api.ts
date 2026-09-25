import type { RunCosts } from './model'

/** `GET /api/runs/{id}/costs` — Langfuse first, the local record behind it. */
export async function fetchCosts(runId: string): Promise<RunCosts> {
  const response = await fetch(`/api/runs/${runId}/costs`)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return (await response.json()) as RunCosts
}
