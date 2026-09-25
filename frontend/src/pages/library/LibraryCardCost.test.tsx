import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { LibraryView } from './LibraryView'
import type { Run } from '@/shared/api/types'

/** SPEC-EXAM-008 AC-6: the novel's total $, with its provenance, on its card. */

const run: Run = {
  id: 'done', slug: 'the-other-side', title: 'The Other Side', premise: 'A hill.',
  profile: 'exam', tone: null, stage: 'complete', halted: null, halted_detail: null,
  source: 'v2', started_at: '2026-09-24T10:00:00Z', finished_at: '2026-09-24T11:00:00Z',
  cost_total: { usd: 74.2047, provenance: 'measured', changes: 2, absent: 1, incomplete: 0, source: 'local' },
}

const html = (runs: Run[]) => renderToStaticMarkup(
  <LibraryView view="library" runs={runs} binned={[]} confirming={null}
    notice={null} error={null} onView={() => {}} onOpen={() => {}} onNew={() => {}}
    onContinue={() => {}} onTrash={() => {}} onConfirmTrash={() => {}}
    onCancelTrash={() => {}} onRestore={() => {}} />)

describe('the Library card carries the novel total', () => {
  it('shows the total, its provenance and the changes with no figure', () => {
    const card = html([run])
    expect(card).toContain('Total cost: $74.20')
    expect(card).toContain('measured')
    expect(card).toContain('1 change not measured')
  })

  it('shows nothing about cost on an older server', () => {
    expect(html([{ ...run, cost_total: undefined }])).not.toContain('Total cost')
  })
})
