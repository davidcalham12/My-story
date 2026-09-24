import type { Run } from '@/shared/api/types'
import { usd } from '@/shared/lib/provenance'
import { Provenance } from '@/shared/ui/Provenance'
import { haltReason } from '@/entities/run/lib'
import { stepOf, titleOf } from '@/entities/run/status'

/**
 * "Continue", before anything is spent (SPEC-EXAM-007 §2).
 *
 * Three things are shown first: why the novel stopped, what it has spent —
 * measured, or absent, never $0 — and where it continues from. Nothing is asked
 * (§8): the ceiling is the profile's, fresh for this continuation, and is shown
 * as information. A run that would stop on the 100k ceiling again is refused
 * with the reason.
 *
 * Pure: every value and every action comes in as a prop.
 */
export function ContinueDialog({ run, busy, error, onConfirm, onCancel }: {
  run: Run
  busy: boolean
  error: string | null
  onConfirm: () => void
  onCancel: () => void
}) {
  const ready = !busy && !run.context_refusal
  const why = haltReason(run) ?? 'it ended before its last chapters were written'

  return (
    <div className="scrim" onClick={onCancel}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="continue-title"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="eyebrow eyebrow--brand">Continue</p>
        <h2 id="continue-title">{titleOf(run)}</h2>

        <dl className="facts">
          <dt>Why it stopped</dt>
          <dd>
            {why}
            {run.halted_detail && <span className="hint"> — {run.halted_detail}</span>}
          </dd>
          <dt>Spent so far</dt>
          <dd>{usd(run.spent_usd)} <Provenance grade={run.spent_provenance ?? 'absent'} /></dd>
          <dt>Continues from</dt>
          <dd>
            {run.resume_stage ? stepOf(run.resume_stage) : 'the first unit not on disk'}
            {run.resume_from && <span className="hint"> ({run.resume_from})</span>}
          </dd>
        </dl>

        <p className="hint">
          It runs on the profile’s current models, the cheapest configuration in use today.
          Chapters already in the book are kept; every new one passes the same gate.
        </p>

        {run.context_refusal ? (
          <p className="panel panel--bad">{run.context_refusal}</p>
        ) : (
          <p>
            Ceiling for this continuation: <strong>{usd(run.ceiling_usd)}</strong>
            <span className="hint"> — the profile’s, fresh for this continuation. A safety net: it stops the run if reached.</span>
          </p>
        )}

        {error && <p className="panel panel--bad">{error}</p>}

        <div className="dialog__actions">
          <button type="button" onClick={onCancel}>Cancel</button>
          <button type="button" className="primary" disabled={!ready} onClick={onConfirm}>
            Continue
          </button>
        </div>
      </div>
    </div>
  )
}
