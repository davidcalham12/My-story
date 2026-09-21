import { MARK, MEANING } from '@/shared/lib/provenance'
import type { Provenance as Grade } from '@/shared/api/types'

/** A figure never appears without saying where it came from. */
export function Provenance({ grade }: { grade: Grade }) {
  return (
    <abbr className={`prov prov--${grade}`} title={`${grade} — ${MEANING[grade]}`}>
      {MARK[grade]}
    </abbr>
  )
}
