import { describe, expect, it, vi } from 'vitest'
import { isValidElement, type ReactElement, type ReactNode } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { LibraryView } from './LibraryView'
import { ContinueDialog } from './ContinueDialog'
import type { Run } from '@/shared/api/types'

/**
 * SPEC-EXAM-007 AC-6: stopped novels, in the panel.
 *
 * Rendered to a string for what the owner reads, and walked as an element tree
 * for what a button does — the suite runs in `node`, with no DOM to click in,
 * and the views are pure so their handlers can be called directly.
 */

const run = (over: Partial<Run>): Run => ({
  id: 'r1', slug: 'finisterre', title: 'Finisterre', premise: 'A lighthouse at the end of the world.',
  profile: 'eval', tone: null, stage: 'FLOW-3', halted: 'budget',
  halted_detail: 'spent $25.80 against a ceiling of $25.00', source: 'v2',
  started_at: '2026-09-24T10:00:00Z', finished_at: '2026-09-24T11:00:00Z',
  trashed_at: null, live: false, complete: false, stopped: true,
  resume_from: 'outline-audit', resume_stage: 'FLOW-3',
  spent_usd: 25.8, spent_provenance: 'measured',
  ceiling_usd: 25, context_refusal: null,
  published_chapters: null, chapters_planned: 10, published_versions: [],
  ...over,
})

const STOPPED = run({ id: 'stopped' })
const COMPLETE = run({
  id: 'done', slug: 'the-other-side', title: 'The Other Side', halted: null, stage: 'complete',
  complete: true, stopped: false, resume_from: null, resume_stage: null,
  published_chapters: 10, published_versions: [1, 2, 3],
})
const LIVE = run({
  id: 'live', slug: 'being-written', halted: null, stage: 'FLOW-4', live: true, stopped: false,
  finished_at: null,
})
const BINNED = run({ id: 'binned', slug: 'leo-and-bruno', title: 'Leo and Bruno', trashed_at: '2026-09-24T12:00:00Z' })

type Props = Parameters<typeof LibraryView>[0]

const props = (over: Partial<Props> = {}): Props => ({
  view: 'library',
  runs: [STOPPED, COMPLETE, LIVE],
  binned: [BINNED],
  confirming: null,
  notice: null,
  error: null,
  onView: () => {},
  onOpen: () => {},
  onNew: () => {},
  onContinue: () => {},
  onTrash: () => {},
  onConfirmTrash: () => {},
  onCancelTrash: () => {},
  onRestore: () => {},
  ...over,
})

/** Every element in a tree, without rendering function components. */
function elements(node: ReactNode): ReactElement[] {
  if (Array.isArray(node)) return node.flatMap(elements)
  if (!isValidElement(node)) return []
  const kids = (node.props as { children?: ReactNode }).children
  return [node, ...elements(kids)]
}

function text(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(text).join('')
  if (isValidElement(node)) return text((node.props as { children?: ReactNode }).children)
  return ''
}

/** The buttons a card (by run id) or the whole view carries, by label. */
function button(tree: ReactNode, label: string, scope?: string): ReactElement<{ onClick: () => void; disabled?: boolean }> {
  const root = scope
    ? elements(tree).find((e) => (e.props as Record<string, unknown>)['data-run'] === scope)
    : tree
  expect(root, `no card for ${scope}`).toBeTruthy()
  const found = elements(root as ReactNode).find((e) => e.type === 'button' && text(e) === label)
  expect(found, `no button "${label}"${scope ? ` on ${scope}` : ''}`).toBeTruthy()
  return found as ReactElement<{ onClick: () => void; disabled?: boolean }>
}

const card = (html: string, id: string) => {
  const start = html.indexOf(`data-run="${id}"`)
  expect(start, `no card for ${id}`).toBeGreaterThan(-1)
  const next = html.indexOf('data-run="', start + 1)
  return html.slice(start, next === -1 ? undefined : next)
}

describe('AC-6: a stopped card offers both; §8: every novel but a live one can be binned', () => {
  it('shows "Continue" and "Move to bin" on a stopped novel', () => {
    const html = renderToStaticMarkup(<LibraryView {...props()} />)
    expect(card(html, 'stopped')).toContain('Continue')
    expect(card(html, 'stopped')).toContain('Move to bin')
  })

  it('offers "Move to bin" but not "Continue" on a complete novel', () => {
    const html = renderToStaticMarkup(<LibraryView {...props()} />)
    expect(card(html, 'done')).toContain('Move to bin')
    expect(card(html, 'done')).not.toContain('Continue')
  })

  it('offers neither on a live one', () => {
    const html = renderToStaticMarkup(<LibraryView {...props()} />)
    expect(card(html, 'live')).not.toContain('Continue')
    expect(card(html, 'live')).not.toContain('Move to bin')
  })

  it('treats a run that ended "complete" with units missing as stopped', () => {
    // The example novel stopped itself at 8/10 with stage = complete (§7.1).
    const eightOfTen = run({ id: 'eight', halted: null, stage: 'complete', stopped: true, resume_from: 'chapter 9', resume_stage: 'FLOW-4' })
    const html = renderToStaticMarkup(<LibraryView {...props({ runs: [eightOfTen] })} />)
    expect(card(html, 'eight')).toContain('Continue')
  })

  it('"Continue" opens the continuation for that run', () => {
    const onContinue = vi.fn()
    button(LibraryView(props({ onContinue })), 'Continue', 'stopped').props.onClick()
    expect(onContinue).toHaveBeenCalledWith(STOPPED)
  })
})

describe('the card says what the book holds, from the list alone', () => {
  it('shows a stopped novel with a one-chapter v1 as stopped with a partial book, never ready', () => {
    const partial = run({ id: 'partial', halted: 'user', published_chapters: 1, published_versions: [1] })
    const html = renderToStaticMarkup(<LibraryView {...props({ runs: [partial] })} />)
    expect(card(html, 'partial')).toContain('Stopped · partial book readable (1 of 10 chapters)')
    expect(card(html, 'partial')).not.toContain('Ready to read')
    expect(html).toContain('0 being written · 0 ready · 1 stopped')
  })

  it('shows "Checking…" while the server has not said, rather than a state it may leave', () => {
    const unknown = run({ id: 'unknown', halted: null, stage: 'complete', stopped: false, published_chapters: undefined })
    const html = renderToStaticMarkup(<LibraryView {...props({ runs: [unknown] })} />)
    expect(card(html, 'unknown')).toContain('Checking…')
    expect(card(html, 'unknown')).not.toContain('Ready to read')
    expect(card(html, 'unknown')).not.toContain('Stopped')
  })
})

describe('AC-6: the bin asks once, and restores', () => {
  it('asks for one confirmation before moving anything', () => {
    const onTrash = vi.fn()
    const onConfirmTrash = vi.fn()
    button(LibraryView(props({ onTrash, onConfirmTrash })), 'Move to bin', 'stopped').props.onClick()
    expect(onTrash).toHaveBeenCalledWith(STOPPED)
    expect(onConfirmTrash).not.toHaveBeenCalled()

    const asking = props({ confirming: 'stopped', onConfirmTrash })
    expect(card(renderToStaticMarkup(<LibraryView {...asking} />), 'stopped')).toMatch(/to the bin\?/)
    button(LibraryView(asking), 'Yes, move', 'stopped').props.onClick()
    expect(onConfirmTrash).toHaveBeenCalledWith(STOPPED)
  })

  it('names a complete novel’s versions before binning it', () => {
    const onConfirmTrash = vi.fn()
    const asking = props({ confirming: 'done', onConfirmTrash })
    const html = card(renderToStaticMarkup(<LibraryView {...asking} />), 'done')
    expect(html).toMatch(/to the bin\?/)
    expect(html).toContain('v1, v2, v3 will be moved to the bin')
    button(LibraryView(asking), 'Yes, move', 'done').props.onClick()
    expect(onConfirmTrash).toHaveBeenCalledWith(COMPLETE)
  })

  it('has a "Bin" view that lists binned runs, and only those', () => {
    const html = renderToStaticMarkup(<LibraryView {...props({ view: 'bin' })} />)
    expect(html).toContain('Leo and Bruno')
    expect(html).not.toContain('Finisterre')
    expect(card(html, 'binned')).toContain('Restore')
    expect(card(html, 'binned')).not.toContain('Continue')
  })

  it('"Restore" restores that run', () => {
    const onRestore = vi.fn()
    button(LibraryView(props({ view: 'bin', onRestore })), 'Restore', 'binned').props.onClick()
    expect(onRestore).toHaveBeenCalledWith(BINNED)
  })

  it('opens the bin from the library, and says how many are in it', () => {
    const onView = vi.fn()
    const tab = button(LibraryView(props({ onView })), 'Bin (1)')
    tab.props.onClick()
    expect(onView).toHaveBeenCalledWith('bin')
  })

  it('counts only the library, never the bin', () => {
    const html = renderToStaticMarkup(<LibraryView {...props()} />)
    expect(html).toContain('1 being written · 1 ready · 1 stopped')
  })
})

type DialogProps = Parameters<typeof ContinueDialog>[0]

const dialog = (over: Partial<DialogProps> = {}): DialogProps => ({
  run: STOPPED, busy: false, error: null,
  onConfirm: () => {}, onCancel: () => {},
  ...over,
})

describe('AC-6: before anything starts, the panel says what it knows', () => {
  it('says why it stopped, what it spent (measured) and where it continues', () => {
    const html = renderToStaticMarkup(<ContinueDialog {...dialog()} />)
    expect(html).toContain('cost ceiling was reached')
    expect(html).toContain('$25.80')
    expect(html).toContain('prov--measured')
    expect(html).toContain('planning the chapters')
    expect(html).toContain('outline-audit')
  })

  it('shows a spend nobody measured as absent, never as $0', () => {
    const html = renderToStaticMarkup(
      <ContinueDialog {...dialog({ run: run({ spent_usd: null, spent_provenance: 'absent' }) })} />)
    expect(html).toContain('not measured')
    expect(html).toContain('prov--absent')
    expect(html).not.toContain('$0.00')
  })

  it('never asks for a figure, even after a budget halt: it shows the ceiling as information', () => {
    const html = renderToStaticMarkup(<ContinueDialog {...dialog({ run: run({ halted_detail: null, ceiling_usd: 25 }) })} />)
    expect(html).not.toContain('<input')
    expect(html).toMatch(/Ceiling for this continuation: <strong>\$25\.00<\/strong>/)
    expect(html).toContain('the profile’s, fresh for this continuation')
    const onConfirm = vi.fn()
    const go = button(ContinueDialog(dialog({ onConfirm })), 'Continue')
    expect(go.props.disabled).toBe(false)
    go.props.onClick()
    expect(onConfirm).toHaveBeenCalled()
  })

  it('does not ask either when the spend was never measured', () => {
    const unmeasured = run({ halted: 'user', spent_usd: null, spent_provenance: 'absent' })
    const html = renderToStaticMarkup(<ContinueDialog {...dialog({ run: unmeasured })} />)
    expect(html).not.toContain('<input')
    expect(button(ContinueDialog(dialog({ run: unmeasured })), 'Continue').props.disabled).toBe(false)
  })

  it('refuses, and says why, a run that would stop on the 100k ceiling again', () => {
    const again = run({ halted: 'context', context_refusal: 'chapter 1 would be sent the same packet again: estimated 104,000 tokens' })
    const html = renderToStaticMarkup(<ContinueDialog {...dialog({ run: again })} />)
    expect(html).toContain('estimated 104,000 tokens')
    expect(button(ContinueDialog(dialog({ run: again })), 'Continue').props.disabled).toBe(true)
  })

  it('shows the backend’s refusal as it came', () => {
    const html = renderToStaticMarkup(<ContinueDialog {...dialog({ error: 'a run is already in flight; the queue is one' })} />)
    expect(html).toContain('already in flight')
  })
})
