import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { CostsView } from './CostsSection'
import { CostTotalLine } from '@/entities/cost/CostTotalLine'
import type { ChangeCost, RunCosts } from '@/entities/cost/model'

/**
 * SPEC-EXAM-008 AC-6: the novel page's Costs section, and the card's total.
 * Rendered to a string, with the endpoint's answer handed in as a prop.
 */

const row = (over: Partial<ChangeCost>): ChangeCost => ({
  n: 1, kind: 'generate', label: null, version: null, chapters: null,
  started_at: '2026-09-24T15:24:29Z', finished_at: '2026-09-24T17:23:00Z',
  minutes: 118.6, total_usd: 53.17, orchestrator_model: 'claude-opus-5[1m]',
  orchestrator_usd: 48.79, agents_model: 'claude-haiku-4-5-20251001', agents_usd: 4.38,
  provenance: 'measured', note: null, results: 1, unresulted: 0, incomplete: 0,
  no_orchestrator: false, source: 'langfuse', confirmed: true, status: 'confirmed in Langfuse',
  trace_id: 'abc', trace_url: 'https://lf.example/project/p/traces/abc', disagreement: null,
  ...over,
})

const costs = (rows: ChangeCost[], over: Partial<RunCosts> = {}): RunCosts => ({
  run_id: 'r1', session_id: 'the-other-side-of-the-hill', langfuse: 'ok', rows,
  total: { usd: 74.2, provenance: 'measured', changes: rows.length, absent: 0, incomplete: 0, source: 'langfuse' },
  ...over,
})

const render = (c: RunCosts | null, error: string | null = null) =>
  renderToStaticMarkup(<CostsView costs={c} error={error} />)

describe('AC-6: the Costs section, one row per change', () => {
  it('shows what, when, minutes, total, orchestrator and agents with model and $', () => {
    const html = render(costs([row({})]))
    expect(html).toContain('Costs')
    expect(html).toContain('First generation')
    expect(html).toContain('2026-09-24')
    expect(html).toContain('118.6')
    expect(html).toContain('$53.17')
    expect(html).toContain('Opus')
    expect(html).toContain('$48.79')
    expect(html).toContain('Haiku')
    expect(html).toContain('$4.38')
  })

  it('says Langfuse ✓ and links the trace when Langfuse confirms the row', () => {
    const html = render(costs([row({})]))
    expect(html).toContain('Langfuse ✓')
    expect(html).toContain('href="https://lf.example/project/p/traces/abc"')
  })

  it('marks a local row unconfirmed in Langfuse, with no link', () => {
    const html = render(costs([row({ source: 'local', confirmed: false, status: 'unconfirmed in Langfuse', trace_url: null })],
      { langfuse: 'unreachable' }))
    expect(html).toContain('local')
    expect(html).toContain('unconfirmed in Langfuse')
    expect(html).not.toContain('Langfuse ✓')
  })

  it('shows both figures when Langfuse and the local record disagree', () => {
    const html = render(costs([row({
      source: 'both', confirmed: false, status: 'Langfuse and the local record disagree; both are shown',
      disagreement: { local: { total_usd: 53.17, orchestrator_usd: 48.79, agents_usd: 4.38 },
                      langfuse: { total_usd: 44.38, orchestrator_usd: 40, agents_usd: 4.38 } },
    })]))
    expect(html).toContain('$53.17')
    expect(html).toContain('$44.38')
    expect(html).toContain('disagree')
  })

  it('never shows an absent figure as $0', () => {
    const html = render(costs([row({
      n: 3, kind: 'reader_change', version: 2, chapters: [3], total_usd: null, minutes: null,
      orchestrator_usd: null, agents_usd: null, orchestrator_model: null, agents_model: null,
      provenance: 'absent', note: 'no stream was kept for this change',
      source: 'local', confirmed: false, trace_url: null,
    })], { total: { usd: null, provenance: 'absent', changes: 1, absent: 1, incomplete: 0, source: 'local' } }))
    expect(html).not.toContain('$0')
    expect(html).toContain('not measured')
    expect(html).toContain('Reader change')
  })

  it('names the processes that sent no result', () => {
    const html = render(costs([row({ unresulted: 2, incomplete: 2 })]))
    expect(html).toContain('incomplete: 2 processes without a result')
  })

  it('says the python loop has no orchestrator rather than $0', () => {
    const html = render(costs([row({ orchestrator_model: null, orchestrator_usd: null, no_orchestrator: true })]))
    expect(html).toContain('no orchestrator (python loop)')
  })

  it('puts the novel total at the bottom, and counts the changes with no figure', () => {
    const html = render(costs([row({}), row({ n: 2, total_usd: null, provenance: 'absent' })],
      { total: { usd: 74.2, provenance: 'measured', changes: 2, absent: 1, incomplete: 0, source: 'mixed' } }))
    const foot = html.slice(html.indexOf('<tfoot'))
    expect(foot).toContain('Novel total')
    expect(foot).toContain('$74.20')
    expect(foot).toContain('1 change not measured')
  })

  it('says so when there is nothing yet, and when the request failed', () => {
    expect(render(costs([]))).toContain('No change to this novel has a cost record yet')
    expect(render(null, 'HTTP 500')).toContain('HTTP 500')
    expect(render(null)).toContain('Reading the costs')
  })
})

describe('AC-6: the Library card total', () => {
  it('shows the total with its provenance and says it is local', () => {
    const html = renderToStaticMarkup(
      <CostTotalLine total={{ usd: 74.2047, provenance: 'measured', changes: 2, absent: 0, incomplete: 0, source: 'local' }} />)
    expect(html).toContain('$74.20')
    expect(html).toContain('measured')
    expect(html).toContain('local')
  })

  it('says not measured, never $0, when no change has a figure', () => {
    const html = renderToStaticMarkup(
      <CostTotalLine total={{ usd: null, provenance: 'absent', changes: 1, absent: 1, incomplete: 0, source: 'local' }} />)
    expect(html).toContain('not measured')
    expect(html).not.toContain('$0')
  })

  it('renders nothing on an older server that sends no total', () => {
    expect(renderToStaticMarkup(<CostTotalLine total={undefined} />)).toBe('')
  })
})
