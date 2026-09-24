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
  asks_for_figure: true, figure_reason: 'this novel stopped on its budget ceiling',
  ceiling_left_usd: null, context_refusal: null,
  ...over,
})

const STOPPED = run({ id: 'stopped' })
const COMPLETE = run({
  id: 'done', slug: 'the-other-side', title: 'The Other Side', halted: null, stage: 'complete',
  complete: true, stopped: false, resume_from: null, resume_stage: null,
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
  published: { done: true },
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

describe('AC-6: a stopped card offers both, and nothing else does', () => {
  it('shows "Continuar" and "Mover a la papelera" on a stopped novel', () => {
    const html = renderToStaticMarkup(<LibraryView {...props()} />)
    expect(card(html, 'stopped')).toContain('Continuar')
    expect(card(html, 'stopped')).toContain('Mover a la papelera')
  })

  it('offers neither on a complete novel or a live one', () => {
    const html = renderToStaticMarkup(<LibraryView {...props()} />)
    for (const id of ['done', 'live']) {
      expect(card(html, id)).not.toContain('Continuar')
      expect(card(html, id)).not.toContain('Mover a la papelera')
    }
  })

  it('treats a run that ended "complete" with units missing as stopped', () => {
    // The example novel stopped itself at 8/10 with stage = complete (§7.1).
    const eightOfTen = run({ id: 'eight', halted: null, stage: 'complete', stopped: true, resume_from: 'chapter 9', resume_stage: 'FLOW-4' })
    const html = renderToStaticMarkup(<LibraryView {...props({ runs: [eightOfTen] })} />)
    expect(card(html, 'eight')).toContain('Continuar')
  })

  it('"Continuar" opens the continuation for that run', () => {
    const onContinue = vi.fn()
    button(LibraryView(props({ onContinue })), 'Continuar', 'stopped').props.onClick()
    expect(onContinue).toHaveBeenCalledWith(STOPPED)
  })
})

describe('AC-6: the bin asks once, and restores', () => {
  it('asks for one confirmation before moving anything', () => {
    const onTrash = vi.fn()
    const onConfirmTrash = vi.fn()
    button(LibraryView(props({ onTrash, onConfirmTrash })), 'Mover a la papelera', 'stopped').props.onClick()
    expect(onTrash).toHaveBeenCalledWith(STOPPED)
    expect(onConfirmTrash).not.toHaveBeenCalled()

    const asking = props({ confirming: 'stopped', onConfirmTrash })
    expect(card(renderToStaticMarkup(<LibraryView {...asking} />), 'stopped')).toMatch(/papelera\?/)
    button(LibraryView(asking), 'Sí, mover', 'stopped').props.onClick()
    expect(onConfirmTrash).toHaveBeenCalledWith(STOPPED)
  })

  it('has a "Papelera" view that lists binned runs, and only those', () => {
    const html = renderToStaticMarkup(<LibraryView {...props({ view: 'bin' })} />)
    expect(html).toContain('Leo and Bruno')
    expect(html).not.toContain('Finisterre')
    expect(card(html, 'binned')).toContain('Restaurar')
    expect(card(html, 'binned')).not.toContain('Continuar')
  })

  it('"Restaurar" restores that run', () => {
    const onRestore = vi.fn()
    button(LibraryView(props({ view: 'bin', onRestore })), 'Restaurar', 'binned').props.onClick()
    expect(onRestore).toHaveBeenCalledWith(BINNED)
  })

  it('opens the bin from the library, and says how many are in it', () => {
    const onView = vi.fn()
    const tab = button(LibraryView(props({ onView })), 'Papelera (1)')
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
  run: STOPPED, ceiling: '', busy: false, error: null,
  onCeiling: () => {}, onConfirm: () => {}, onCancel: () => {},
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

  it('asks for a ceiling in USD when the halt was budget, and waits for it', () => {
    const html = renderToStaticMarkup(<ContinueDialog {...dialog()} />)
    expect(html).toContain('type="number"')
    expect(html).toContain('USD')
    expect(button(ContinueDialog(dialog()), 'Continuar').props.disabled).toBe(true)
    expect(button(ContinueDialog(dialog({ ceiling: '0' })), 'Continuar').props.disabled).toBe(true)

    const onConfirm = vi.fn()
    const ready = button(ContinueDialog(dialog({ ceiling: '40', onConfirm })), 'Continuar')
    expect(ready.props.disabled).toBe(false)
    ready.props.onClick()
    expect(onConfirm).toHaveBeenCalled()
  })

  it('does not ask when the profile still has room, and says how much', () => {
    const roomy = run({ halted: 'user', asks_for_figure: false, figure_reason: null, ceiling_left_usd: 15, spent_usd: 10 })
    const html = renderToStaticMarkup(<ContinueDialog {...dialog({ run: roomy })} />)
    expect(html).not.toContain('type="number"')
    expect(html).toContain('$15.00')
    expect(button(ContinueDialog(dialog({ run: roomy })), 'Continuar').props.disabled).toBe(false)
  })

  it('refuses, and says why, a run that would stop on the 100k ceiling again', () => {
    const again = run({ halted: 'context', asks_for_figure: false, context_refusal: 'chapter 1 would be sent the same packet again: estimated 104,000 tokens' })
    const html = renderToStaticMarkup(<ContinueDialog {...dialog({ run: again })} />)
    expect(html).toContain('estimated 104,000 tokens')
    expect(button(ContinueDialog(dialog({ run: again })), 'Continuar').props.disabled).toBe(true)
  })

  it('shows the backend’s refusal as it came', () => {
    const html = renderToStaticMarkup(<ContinueDialog {...dialog({ error: 'a run is already in flight; the queue is one' })} />)
    expect(html).toContain('already in flight')
  })
})
